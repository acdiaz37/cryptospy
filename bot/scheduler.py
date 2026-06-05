import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from telegram.ext import Application

from config import settings
from models.signal import SignalRecord
from services.grok import GrokClient
from services.coingecko import CoinGeckoClient
from services.sheets import SheetsClient

logger = logging.getLogger(__name__)


class BotScheduler:
    def __init__(self, telegram_app: Application):
        self.app = telegram_app
        self.scheduler = AsyncIOScheduler()
        self.grok = GrokClient()
        self.coingecko = CoinGeckoClient()
        self.sheets = SheetsClient()

    def start(self):
        """Inicia el scheduler y programa tareas pendientes al reiniciar."""
        self.scheduler.start()
        # Programar análisis periódico
        self._schedule_analysis()
        # Re-programar verificaciones de señales PENDING
        import asyncio
        asyncio.create_task(self._restore_pending_checks())
        logger.info("Scheduler started with window=%dh", settings.ANALYSIS_WINDOW_HOURS)

    def _schedule_analysis(self, force_now: bool = False):
        """Programa el análisis periódico según ANALYSIS_WINDOW_HOURS.
        
        Si force_now=False, consulta el historial para evitar ejecutar Grok
        innecesariamente al reiniciar el bot.
        """
        from datetime import timezone
        # Quitar job anterior si existe
        self.scheduler.remove_all_jobs(jobstore=None)
        
        next_run = datetime.now(timezone.utc)
        
        if not force_now:
            last_ts = self.sheets.get_last_signal_timestamp()
            if last_ts:
                window = timedelta(hours=settings.ANALYSIS_WINDOW_HOURS)
                elapsed = datetime.now(timezone.utc) - last_ts
                if elapsed < window:
                    # Aún no toca, esperar hasta completar la ventana
                    next_run = last_ts + window
                    logger.info(
                        "Last analysis was %s ago. Skipping immediate run. Next analysis at %s",
                        elapsed,
                        next_run
                    )
                else:
                    logger.info("Last analysis was %s ago. Running now.", elapsed)
            else:
                logger.info("No previous analysis found. Running now.")
        else:
            logger.info("Forced immediate analysis.")
        
        trigger = IntervalTrigger(hours=settings.ANALYSIS_WINDOW_HOURS)
        self.scheduler.add_job(
            self._run_analysis,
            trigger=trigger,
            id="periodic_analysis",
            replace_existing=True,
            next_run_time=next_run,
        )
        logger.info("Next analysis scheduled for %s", next_run)

    def reschedule_analysis(self):
        """Re-programa el análisis cuando cambia la ventana de tiempo."""
        self._schedule_analysis()

    async def _restore_pending_checks(self):
        """Al reiniciar, lee señales PENDING del sheet y programa sus checks."""
        try:
            pending = self.sheets.get_pending_signals()
            for sig in pending:
                # Calcular cuánto falta desde ahora hasta que debería verificarse
                # Usamos el timestamp de la señal + analysis_window_hours
                try:
                    signal_time = datetime.fromisoformat(sig.timestamp_utc.replace("Z", "+00:00"))
                    check_time = signal_time + timedelta(hours=sig.analysis_window_hours)
                    now = datetime.now(signal_time.tzinfo)
                    if check_time > now:
                        self.scheduler.add_job(
                            self._run_verification,
                            trigger="date",
                            run_date=check_time,
                            args=[sig.signal_id, sig.pair, sig.entry_price, sig.direction,
                                  sig.expected_min_pct, sig.expected_max_pct],
                            id=f"verify_{sig.signal_id}",
                            replace_existing=True,
                        )
                        logger.info("Restored verification for %s at %s", sig.signal_id, check_time)
                    else:
                        # Ya debería haberse verificado, marcar como STALE
                        logger.warning("Signal %s is stale, marking as STALE", sig.signal_id)
                        # No actualizamos el sheet aquí para no bloquear el arranque
                except Exception as e:
                    logger.warning("Error restoring signal %s: %s", sig.signal_id, e)
        except Exception as e:
            logger.error("Error restoring pending checks: %s", e)

    async def _send_progress(self, chat_id: int | None, message: str) -> None:
        """Envía mensaje de progreso a Telegram y loguea en consola."""
        # Limpiar emojis para la consola (Windows no los soporta bien)
        clean = message.replace("🔮", "[ANALISIS]").replace("📊", "[PRECIOS]").replace("🤖", "[GROK]").replace("💾", "[SHEET]").replace("✅", "[OK]").replace("❌", "[ERROR]")
        logger.info(clean)
        if chat_id:
            try:
                await self.app.bot.send_message(chat_id, message, parse_mode="HTML")
            except Exception:
                pass

    async def _run_analysis(self):
        """Ejecuta el análisis completo: precios -> Grok -> Sheet -> notificación."""
        from datetime import timezone
        chat_id = self._get_owner_chat_id()
        try:
            await self._send_progress(chat_id, "🔮 <b>Iniciando análisis...</b>")

            # 1. Obtener precios actuales
            await self._send_progress(chat_id, "📊 <b>Consultando precios en CoinGecko...</b>")
            prices = await self.coingecko.get_prices()
            if not prices:
                await self._send_progress(chat_id, "❌ <b>Error:</b> No se pudieron obtener precios de CoinGecko.")
                return
            await self._send_progress(chat_id, f"✅ <b>Precios obtenidos:</b> {len(prices)} activos.")

            # 2. Llamar a Grok
            await self._send_progress(chat_id, "🤖 <b>Consultando Grok/xAI...</b>")
            response = await self.grok.fetch_signals()
            if not response:
                await self._send_progress(chat_id, "❌ <b>Error:</b> Grok no devolvió respuesta. Revisá los logs.")
                return
            await self._send_progress(
                chat_id,
                f"✅ <b>Grok respondió:</b> {response.selection_summary.signals_selected} señales detectadas."
            )

            # 3. Procesar cada señal
            await self._send_progress(chat_id, "💾 <b>Guardando señales en Google Sheets...</b>")
            count = 0
            for sig in response.signals:
                symbol = sig.pair.replace("/USDT", "").replace("/USD", "").upper()
                gecko_id = self.coingecko.id_from_symbol(symbol)
                if not gecko_id or gecko_id not in prices:
                    logger.warning("No price found for %s (symbol=%s)", sig.pair, symbol)
                    continue

                entry_price = prices[gecko_id]
                min_pct = sig.expected_move_pct.min
                max_pct = sig.expected_move_pct.max

                if sig.direction == "LONG":
                    target_min = entry_price * (1 + min_pct / 100)
                    target_max = entry_price * (1 + max_pct / 100)
                else:
                    target_min = entry_price * (1 - min_pct / 100)
                    target_max = entry_price * (1 - max_pct / 100)

                signal_id = f"{response.timestamp_utc}_{sig.rank}"
                record = SignalRecord(
                    rank=sig.rank,
                    signal_id=signal_id,
                    timestamp_utc=response.timestamp_utc,
                    analysis_window_hours=response.analysis_window_hours,
                    pair=sig.pair,
                    asset_name=sig.asset_name,
                    direction=sig.direction,
                    entry_price=entry_price,
                    expected_min_pct=min_pct,
                    expected_max_pct=max_pct,
                    target_price_min=round(target_min, 8),
                    target_price_max=round(target_max, 8),
                    confidence_score=sig.confidence_score,
                    bullish_score=sig.bullish_score,
                    bearish_score=sig.bearish_score,
                    expected_edge=sig.expected_edge,
                    primary_catalyst=sig.primary_catalyst,
                    narrative=sig.narrative,
                )

                self.sheets.append_signal(record)
                count += 1

                # Programar verificación
                check_time = datetime.now(timezone.utc) + timedelta(hours=response.analysis_window_hours)
                self.scheduler.add_job(
                    self._run_verification,
                    trigger="date",
                    run_date=check_time,
                    args=[signal_id, sig.pair, entry_price, sig.direction, min_pct, max_pct],
                    id=f"verify_{signal_id}",
                    replace_existing=True,
                )

            await self._send_progress(chat_id, f"✅ <b>Señales guardadas:</b> {count} en Google Sheets.")

            # 4. Notificar resumen
            if chat_id:
                summary = (
                    f"🎯 <b>Análisis completado</b>\n\n"
                    f"Ventana: {response.analysis_window_hours}h\n"
                    f"Señales: {count} ({response.selection_summary.long_signals} LONG, "
                    f"{response.selection_summary.short_signals} SHORT)\n"
                    f"Sentimiento: {response.market_overview.overall_sentiment}\n\n"
                    f"Usá 📊 <b>Ver Estado</b> para verlas en vivo."
                )
                await self.app.bot.send_message(chat_id, summary, parse_mode="HTML")

        except Exception as e:
            logger.exception("Error in scheduled analysis: %s", e)
            await self._send_progress(chat_id, f"❌ <b>Error en análisis:</b> {e}")

    async def _run_verification(self, signal_id: str, pair: str, entry_price: float,
                                direction: str, expected_min_pct: float, expected_max_pct: float):
        """Verifica una señal al cabo de la ventana de tiempo."""
        chat_id = self._get_owner_chat_id()
        try:
            symbol = pair.replace("/USDT", "").replace("/USD", "").upper()
            gecko_id = self.coingecko.id_from_symbol(symbol)
            if not gecko_id:
                logger.error("Cannot verify: unknown symbol %s", symbol)
                self.sheets.update_signal_check(signal_id, "STALE", 0, 0, "")
                return

            prices = await self.coingecko.get_prices([gecko_id])
            if gecko_id not in prices:
                logger.error("Cannot verify: no price for %s", gecko_id)
                self.sheets.update_signal_check(signal_id, "STALE", 0, 0, "")
                return

            exit_price = prices[gecko_id]
            actual_move = ((exit_price - entry_price) / entry_price) * 100

            # Determinar estado
            if direction == "LONG":
                if exit_price >= entry_price * (1 + expected_max_pct / 100):
                    status = "HIT_MAX"
                    accuracy = "CORRECT"
                elif exit_price >= entry_price * (1 + expected_min_pct / 100):
                    status = "HIT_MIN"
                    accuracy = "CORRECT"
                elif exit_price > entry_price:
                    status = "PARTIAL"
                    accuracy = "PARTIAL"
                else:
                    status = "MISS"
                    accuracy = "INCORRECT"
            else:  # SHORT
                if exit_price <= entry_price * (1 - expected_max_pct / 100):
                    status = "HIT_MAX"
                    accuracy = "CORRECT"
                elif exit_price <= entry_price * (1 - expected_min_pct / 100):
                    status = "HIT_MIN"
                    accuracy = "CORRECT"
                elif exit_price < entry_price:
                    status = "PARTIAL"
                    accuracy = "PARTIAL"
                else:
                    status = "MISS"
                    accuracy = "INCORRECT"

            self.sheets.update_signal_check(
                signal_id, status, round(exit_price, 8), round(actual_move, 4), accuracy
            )

            # Notificar
            if chat_id:
                emoji = "✅" if accuracy == "CORRECT" else ("⚠️" if accuracy == "PARTIAL" else "❌")
                msg = (
                    f"{emoji} <b>Verificación: {pair}</b>\n"
                    f"Dirección: {direction}\n"
                    f"Entry: ${entry_price:,.4f} → Exit: ${exit_price:,.4f}\n"
                    f"Movimiento real: {actual_move:+.2f}%\n"
                    f"Estado: <b>{status}</b> | Precisión: <b>{accuracy}</b>"
                )
                await self.app.bot.send_message(chat_id, msg, parse_mode="HTML")

        except Exception as e:
            logger.exception("Error verifying signal %s: %s", signal_id, e)
            self.sheets.update_signal_check(signal_id, "STALE", 0, 0, "")
            if chat_id:
                await self.app.bot.send_message(
                    chat_id, f"⚠️ Error verificando {pair}: {e}"
                )

    def _get_owner_chat_id(self) -> int | None:
        """Devuelve el chat_id del dueño del bot (primer usuario que interactúa)."""
        # Por simplicidad, almacenamos el chat_id en bot_data la primera vez
        return self.app.bot_data.get("owner_chat_id")
