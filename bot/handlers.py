import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from config import settings
from services.coingecko import CoinGeckoClient
from services.sheets import SheetsClient
from bot.keyboards import main_menu, settings_menu, back_button, refresh_status
from bot.scheduler import BotScheduler

logger = logging.getLogger(__name__)

coingecko = CoinGeckoClient()
sheets = SheetsClient()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mensaje de bienvenida y registro del dueño."""
    chat_id = update.effective_chat.id
    # Registrar dueño si no existe
    if "owner_chat_id" not in context.application.bot_data:
        context.application.bot_data["owner_chat_id"] = chat_id
        logger.info("Owner registered: %s", chat_id)

    text = (
        f"¡Hola {update.effective_user.first_name}! Soy <b>CryptoSpy</b> 🤖\n\n"
        f"Ventana actual: <b>{settings.ANALYSIS_WINDOW_HOURS}h</b>\n\n"
        f"¿Qué querés hacer?"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu())


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando manual para ejecutar análisis inmediatamente."""
    await update.message.reply_text("🔮 Ejecutando análisis...")
    scheduler: BotScheduler = context.application.bot_data.get("scheduler")
    if scheduler:
        await scheduler._run_analysis()
    else:
        await update.message.reply_text("❌ Scheduler no inicializado.")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra estado de señales activas con P&L en vivo."""
    await _send_status(update.effective_chat.id, context)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra menú de configuración."""
    text = (
        f"⚙️ <b>Configuración</b>\n\n"
        f"Ventana de análisis actual: <b>{settings.ANALYSIS_WINDOW_HOURS} horas</b>\n\n"
        f"Seleccioná una nueva ventana:"
    )
    await update.message.reply_text(
        text, parse_mode="HTML", reply_markup=settings_menu(settings.ANALYSIS_WINDOW_HOURS)
    )


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra últimas señales del historial."""
    signals = sheets.get_recent_signals(limit=10)
    if not signals:
        await update.message.reply_text("📜 No hay señales en el historial.", reply_markup=back_button())
        return

    lines = ["📜 <b>Últimas señales</b>\n"]
    for sig in signals:
        status_emoji = {
            "PENDING": "⏳",
            "HIT_MIN": "🟢",
            "HIT_MAX": "🚀",
            "PARTIAL": "🟡",
            "MISS": "🔴",
            "STALE": "⚪",
        }.get(sig.status, "❓")
        acc = sig.accuracy or "PENDIENTE"
        lines.append(
            f"{status_emoji} <b>{sig.pair}</b> | {sig.direction} | Conf: {sig.confidence_score}%\n"
            f"   Entry: ${sig.entry_price:,.4f} | Status: {sig.status} | {acc}\n"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=back_button())


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Rutea todos los callbacks de botones inline."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main_menu":
        text = (
            f"<b>CryptoSpy</b> 🤖\n"
            f"Ventana actual: <b>{settings.ANALYSIS_WINDOW_HOURS}h</b>\n\n"
            f"¿Qué querés hacer?"
        )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_menu())

    elif data == "analyze_now":
        await query.edit_message_text("🔮 Ejecutando análisis...")
        scheduler: BotScheduler = context.application.bot_data.get("scheduler")
        if scheduler:
            await scheduler._run_analysis()
        else:
            await query.edit_message_text("❌ Scheduler no inicializado.", reply_markup=back_button())

    elif data == "view_status":
        await query.edit_message_text("📊 Consultando precios en vivo...")
        await _send_status(update.effective_chat.id, context, edit_message_id=query.message.message_id)

    elif data == "settings":
        text = (
            f"⚙️ <b>Configuración</b>\n\n"
            f"Ventana de análisis actual: <b>{settings.ANALYSIS_WINDOW_HOURS} horas</b>\n\n"
            f"Seleccioná una nueva ventana:"
        )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=settings_menu(settings.ANALYSIS_WINDOW_HOURS))

    elif data.startswith("set_window_"):
        hours = int(data.split("_")[-1])
        settings.ANALYSIS_WINDOW_HOURS = hours
        settings.save()
        # Re-programar scheduler
        scheduler: BotScheduler = context.application.bot_data.get("scheduler")
        if scheduler:
            scheduler.reschedule_analysis()
        text = (
            f"✅ Ventana actualizada a <b>{hours} horas</b>.\n\n"
            f"El próximo análisis y las verificaciones usarán esta nueva ventana."
        )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_button())

    elif data == "history":
        signals = sheets.get_recent_signals(limit=10)
        if not signals:
            await query.edit_message_text("📜 No hay señales en el historial.", reply_markup=back_button())
            return
        lines = ["📜 <b>Últimas señales</b>\n"]
        for sig in signals:
            status_emoji = {
                "PENDING": "⏳",
                "HIT_MIN": "🟢",
                "HIT_MAX": "🚀",
                "PARTIAL": "🟡",
                "MISS": "🔴",
                "STALE": "⚪",
            }.get(sig.status, "❓")
            acc = sig.accuracy or "PENDIENTE"
            lines.append(
                f"{status_emoji} <b>{sig.pair}</b> | {sig.direction} | Conf: {sig.confidence_score}%\n"
                f"   Entry: ${sig.entry_price:,.4f} | Status: {sig.status} | {acc}\n"
            )
        await query.edit_message_text("\n".join(lines), parse_mode="HTML", reply_markup=back_button())


async def _send_status(chat_id: int, context: ContextTypes.DEFAULT_TYPE, edit_message_id: int | None = None) -> None:
    """Construye y envía el mensaje de estado con precios en vivo."""
    signals = sheets.get_pending_signals()
    if not signals:
        text = "📊 No hay señales activas pendientes.\n\nUsá 🔮 <b>Analizar Ahora</b> para generar nuevas."
        if edit_message_id:
            await context.bot.edit_message_text(text, chat_id=chat_id, message_id=edit_message_id,
                                                parse_mode="HTML", reply_markup=back_button())
        else:
            await context.bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=back_button())
        return

    # Obtener precios en vivo para todos los pares pendientes
    symbols = []
    for sig in signals:
        sym = sig.pair.replace("/USDT", "").replace("/USD", "").upper()
        gid = coingecko.id_from_symbol(sym)
        if gid:
            symbols.append(gid)

    prices = {}
    if symbols:
        try:
            prices = await coingecko.get_prices(list(set(symbols)))
        except Exception as e:
            logger.error("Error fetching live prices for status: %s", e)

    lines = [f"📊 <b>Señales Activas</b> ({len(signals)})\n"]
    for sig in signals:
        sym = sig.pair.replace("/USDT", "").replace("/USD", "").upper()
        gid = coingecko.id_from_symbol(sym)
        current_price = prices.get(gid) if gid else None

        if current_price and sig.entry_price:
            pnl_pct = ((current_price - sig.entry_price) / sig.entry_price) * 100
            if sig.direction == "SHORT":
                pnl_pct = -pnl_pct  # Invertir para SHORT
            pnl_emoji = "🟢" if pnl_pct > 0 else ("🔴" if pnl_pct < 0 else "⚪")
            price_line = f"   Entry: ${sig.entry_price:,.4f} → Now: ${current_price:,.4f} ({pnl_emoji} {pnl_pct:+.2f}%)"
        else:
            price_line = f"   Entry: ${sig.entry_price:,.4f} → Now: (no disponible)"

        target_line = f"   Target: ${sig.target_price_min:,.4f} - ${sig.target_price_max:,.4f}"
        lines.append(
            f"#{sig.rank or '?'} <b>{sig.pair}</b> | {sig.direction} | Conf: {sig.confidence_score}%\n"
            f"{price_line}\n"
            f"{target_line}\n"
        )

    text = "\n".join(lines)
    if edit_message_id:
        await context.bot.edit_message_text(text, chat_id=chat_id, message_id=edit_message_id,
                                            parse_mode="HTML", reply_markup=refresh_status())
    else:
        await context.bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=refresh_status())
