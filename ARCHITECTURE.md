# CryptoSpy Bot - Documento de Arquitectura

> Versión: 1.0
> Fecha: 2026-06-04
> Estado: Prueba de 1 mes

---

## 1. Resumen del Proyecto

Bot de Telegram que ejecuta análisis de mercado cripto mediante IA (Grok/xAI) con acceso a X/Twitter, genera señales de trading LONG/SHORT, las registra en Google Sheets y verifica automáticamente si se cumplieron al cabo de una ventana de tiempo parametrizable.

### Flujo resumido
```
[Bot Telegram] --(scheduling)--> [Grok API] --(señales JSON)--> [Google Sheets]
                                      ^                              |
                                      |                              v
                               [X/Twitter data]              [Precio real]
                                                                   |
                                                              [Verificación]
                                                                   |
                                                            [Google Sheets]
```

---

## 2. Stack Tecnológico

| Capa | Tecnología | Motivo |
|------|-----------|--------|
| **Bot** | `python-telegram-bot` v20+ | Async nativo, webhook/polling |
| **IA** | xAI Grok API | Acceso nativo a X/Twitter |
| **Precios** | CoinGecko API (free tier) | Gratis, confiable, no requiere API key para básico |
| **Spreadsheet** | Google Sheets API v4 | Fácil de visualizar, gratuito |
| **Config** | `pydantic-settings` + `.env` | Variables locales y en Fly.io |
| **Scheduler** | `APScheduler` (async) | Tareas parametrizables en background |
| **Deploy** | Fly.io hobby plan | Gratis, Docker nativo |

---

## 3. Formato JSON de Señales (Ajustado LONG/SHORT)

```json
{
  "timestamp_utc": "2026-06-05T00:50:00Z",
  "analysis_window_hours": 24,
  "market_overview": {
    "overall_sentiment": "Cautious optimism with selective altcoin rotation",
    "risk_level": "Medium-High"
  },
  "signals": [
    {
      "rank": 1,
      "pair": "HYPE/USDT",
      "asset_name": "Hyperliquid",
      "direction": "LONG",
      "bullish_score": 91,
      "bearish_score": 12,
      "confidence_score": 88,
      "expected_move_pct": {
        "min": 5,
        "max": 14
      },
      "expected_edge": 1144,
      "primary_catalyst": "Grayscale Hyperliquid ETF launch with lowest US fee (0.29%)",
      "narrative": "Capital rotating hard into high-conviction alts with real product-market fit",
      "supporting_evidence": [
        "Grayscale launched HYPE ETF with strong fundamentals",
        "Lookonchain reports: 902k HYPE (~$65M) withdrawn in past 3 days"
      ],
      "key_accounts_involved": [
        "@lookonchain",
        "@aixbt_agent"
      ],
      "institutional_or_whale_signal": "Confirmed whale accumulation via large exchange withdrawals",
      "risk_factors": [
        "Broader crypto market corrective phase",
        "High volatility typical of alt rotation plays"
      ],
      "reason_for_selection": "Highest confluence of institutional catalyst and verifiable on-chain inflows"
    }
  ],
  "selection_summary": {
    "assets_screened": 50,
    "signals_selected": 5,
    "long_signals": 4,
    "short_signals": 1,
    "selection_method": "expected_edge_ranking"
  }
}
```

### Cambios respecto al formato original
- **`direction`**: Nuevo campo obligatorio (`LONG` o `SHORT`).
- **`bullish_score` + `bearish_score`**: Ambos presentes (antes solo bullish).
- **`expected_edge`**: Nuevo campo calculado (`confidence_score × |expected_move|`).
- **`analysis_window_hours`**: Nuevo campo raíz para trazabilidad de la ventana usada.
- Se eliminó `previous_predictions_review` del prompt principal (se maneja en el spreadsheet).

---

## 4. Prompt Ajustado (Ventana Parametrizable)

El prompt acepta una variable `{{ANALYSIS_WINDOW_HOURS}}` que el bot inyecta antes de enviar a Grok.

```
You are an elite cryptocurrency market intelligence and directional trading system.

# MISSION
Analyze the last {{ANALYSIS_WINDOW_HOURS}} hours of Twitter/X activity and identify the highest-conviction cryptocurrency trading opportunities likely to generate significant directional movement during the next {{ANALYSIS_WINDOW_HOURS}} hours.

Every signal must recommend either: LONG or SHORT.

# PRIMARY DATA SOURCE
Twitter/X is the primary source. At least 70% of evidence must originate from Twitter/X activity in the previous {{ANALYSIS_WINDOW_HOURS}} hours.

# ASSET UNIVERSE
- Bitcoin, Ethereum, Top 50 cryptocurrencies by market cap
- Examples: BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT, LINK/USDT, HYPE/USDT
- Ignore: microcaps, low liquidity tokens, meme coins outside Top 50

# SIGNAL SELECTION RULES
- Rank by Expected Edge = confidence_score × |expected_move_pct|
- Maximum 10 opportunities
- Do not force signals if quality is low
- Avoid duplicate narratives

# SCORING MODEL
- bullish_score: 0-100
- bearish_score: 0-100
- confidence_score: 0-100
- expected_edge: confidence_score × |expected_move_pct|

# PREDICTION REQUIREMENTS
- Direction: LONG or SHORT
- Confidence score
- Expected percentage move (min, max)
- Main catalyst
- Key narrative
- Risk factors
- Time horizon: {{ANALYSIS_WINDOW_HOURS}} hours

# OUTPUT
Return ONLY valid JSON. No markdown, no commentary.

JSON STRUCTURE:
{
  "timestamp_utc": "ISO8601",
  "analysis_window_hours": {{ANALYSIS_WINDOW_HOURS}},
  "market_overview": { ... },
  "signals": [
    {
      "rank": 1,
      "pair": "HYPE/USDT",
      "asset_name": "Hyperliquid",
      "direction": "LONG",
      "bullish_score": 91,
      "bearish_score": 12,
      "confidence_score": 88,
      "expected_move_pct": { "min": 5, "max": 14 },
      "expected_edge": 1144,
      "primary_catalyst": "...",
      "narrative": "...",
      "supporting_evidence": ["..."],
      "key_accounts_involved": ["..."],
      "institutional_or_whale_signal": "...",
      "risk_factors": ["..."],
      "reason_for_selection": "..."
    }
  ],
  "selection_summary": {
    "assets_screened": 50,
    "signals_selected": 5,
    "long_signals": 4,
    "short_signals": 1,
    "selection_method": "expected_edge_ranking"
  }
}
```

---

## 5. Estructura de Google Sheets

**Nombre del archivo**: `CryptoSpy Signals`
**Hoja única** (suficiente para 1 mes de prueba)

### Columnas

| # | Columna | Tipo | Origen | Notas |
|---|---------|------|--------|-------|
| 1 | `signal_id` | Auto | Bot | UUID corto o timestamp+rank |
| 2 | `timestamp_utc` | String | Grok JSON | Cuándo se generó la señal |
| 3 | `analysis_window_hours` | Number | Bot config | Ventana usada (ej: 24) |
| 4 | `pair` | String | Grok JSON | Ej: HYPE/USDT |
| 5 | `asset_name` | String | Grok JSON | Ej: Hyperliquid |
| 6 | `direction` | String | Grok JSON | LONG o SHORT |
| 7 | `entry_price` | Number | CoinGecko | Precio al momento de la señal |
| 8 | `expected_min_pct` | Number | Grok JSON | `expected_move_pct.min` |
| 9 | `expected_max_pct` | Number | Grok JSON | `expected_move_pct.max` |
| 10 | `target_price_min` | Number | Calculado | `entry × (1 + min/100)` o `entry × (1 - min/100)` para SHORT |
| 11 | `target_price_max` | Number | Calculado | `entry × (1 + max/100)` o `entry × (1 - max/100)` para SHORT |
| 12 | `confidence_score` | Number | Grok JSON | 0-100 |
| 13 | `bullish_score` | Number | Grok JSON | 0-100 |
| 14 | `bearish_score` | Number | Grok JSON | 0-100 |
| 15 | `expected_edge` | Number | Grok JSON | Para ranking interno |
| 16 | `primary_catalyst` | String | Grok JSON | Resumen del catalizador |
| 17 | `narrative` | String | Grok JSON | Narrativa detectada |
| 18 | `status` | Enum | Bot (post-check) | `PENDING` → `HIT_MIN` / `HIT_MAX` / `PARTIAL` / `MISS` / `STALE` |
| 19 | `exit_price` | Number | CoinGecko (check) | Precio al cabo de la ventana |
| 20 | `actual_move_pct` | Number | Calculado | `(exit - entry) / entry × 100` con signo |
| 21 | `accuracy` | Enum | Calculado | `CORRECT` / `PARTIAL` / `INCORRECT` |
| 22 | `check_timestamp_utc` | String | Bot | Cuándo se hizo la verificación |
| 23 | `notes` | String | Manual | Campo libre para anotaciones del usuario |

### Estados de `status`
- `PENDING`: Señal activa, aún no se verifica.
- `HIT_MIN`: El precio alcanzó al menos el mínimo esperado.
- `HIT_MAX`: El precio alcanzó el máximo esperado.
- `PARTIAL`: Se movió en la dirección correcta pero no llegó al mínimo.
- `MISS`: Se movió en dirección contraria o lateral.
- `STALE`: No se pudo verificar (API caída, token delistado, etc.).

### Lógica de verificación automática
```
Si direction == LONG:
  Si exit_price >= target_price_max → HIT_MAX
  Si exit_price >= target_price_min → HIT_MIN
  Si exit_price > entry_price → PARTIAL
  Si exit_price <= entry_price → MISS

Si direction == SHORT:
  Si exit_price <= target_price_min → HIT_MAX  (max profit)
  Si exit_price <= target_price_max → HIT_MIN  (min profit)
  Si exit_price < entry_price → PARTIAL
  Si exit_price >= entry_price → MISS
```

> **Nota**: Para el botón "cómo van las cosas" (consulta manual), se calcula P&L en tiempo real usando el precio actual de CoinGecko vs `entry_price`. **No se escribe en el sheet**.

---

## 6. Flujo del Bot (Telegram)

### Comandos

| Comando | Acción | Quién puede |
|---------|--------|-------------|
| `/start` | Mensaje de bienvenida + botones principales | Dueño |
| `/analyze` | Ejecuta análisis manualmente (bypass del scheduler) | Dueño |
| `/status` | Muestra señales activas y su estado actual (P&L en vivo) | Dueño |
| `/settings` | Menú de configuración (ventana de tiempo, etc.) | Dueño |
| `/history` | ltimas N señales con resultado | Dueño |

### Menú Principal (Inline Keyboard)

```
[🔮 Analizar Ahora]  [📊 Ver Estado]
[⚙️ Configuración]   [📜 Historial]
```

### Configuración (ventana parametrizable)

Al tocar `[⚙️ Configuración]`:
```
Ventana de análisis actual: 24 horas

[12 horas]  [24 horas]  [48 horas]
[Personalizado...]

[🔙 Volver]
```

Cambiar la ventana:
1. Actualiza la variable `ANALYSIS_WINDOW_HOURS` en memoria y `.env`.
2. Re-inyecta el nuevo valor en el prompt antes de enviar a Grok.
3. Re-programa el scheduler con la nueva frecuencia.
4. **No afecta señales ya emitidas** (ellas mantienen su ventana original).

### Flujo de "Ver Estado" (`/status` o `[📊 Ver Estado]`)

```
📊 Estado de Señales Activas

#1 HYPE/USDT | LONG | Conf: 88%
   Entry: $70.50 → Now: $75.20 (+6.7%)
   Target: $74.02 - $80.37
   Status: 🟢 HIT_MIN

#2 NEAR/USDT | LONG | Conf: 79%
   Entry: $5.10 → Now: $4.95 (-2.9%)
   Target: $5.30 - $5.66
   Status: 🔴 MISS (aún en ventana)

[🔄 Actualizar]  [📋 Ver detalle #1]
```

> Los precios "Now" se consultan en tiempo real a CoinGecko. No se guardan.

### Flujo de Análisis Automático

```
1. Scheduler dispara cada N horas (N = ANALYSIS_WINDOW_HOURS)
2. Bot consulta precio actual de cada par en el universo vía CoinGecko
   → Guarda precios como "entry_price" para los que salgan en señales
3. Bot inyecta ANALYSIS_WINDOW_HOURS en el prompt
4. Bot envía prompt a Grok API
5. Bot recibe JSON de señales
6. Bot filtra solo los pares que existen en CoinGecko (validación)
7. Bot escribe cada señal como fila en Google Sheets (status: PENDING)
8. Bot programa una tarea de verificación para `now + ANALYSIS_WINDOW_HOURS`
9. Bot envía resumen por Telegram:
   "🔮 Análisis completado. 5 señales generadas. /status para verlas."
```

### Flujo de Verificación Automática (24h después)

```
1. Scheduler dispara la tarea programada para signal_id=X
2. Bot consulta precio actual del par vía CoinGecko
3. Bot calcula target prices, actual_move_pct, accuracy
4. Bot actualiza la fila en Google Sheets:
   - status
   - exit_price
   - actual_move_pct
   - accuracy
   - check_timestamp_utc
5. Bot envía notificación por Telegram:
   "✅ HYPE/USDT (LONG): HIT_MAX (+14% esperado, +15.2% real)"
   o
   "❌ NEAR/USDT (LONG): MISS (-2.9% real vs +4% esperado)"
```

---

## 7. Configuración Parametrizable

Variables guardadas en `.env` y editables vía bot:

| Variable | Default | Editable vía Bot | Descripción |
|----------|---------|------------------|-------------|
| `BOT_TOKEN` | - | No | Token de BotFather |
| `GROK_API_KEY` | - | No | API key de xAI |
| `ANALYSIS_WINDOW_HOURS` | 24 | Sí | Ventana de análisis y verificación |
| `GOOGLE_SHEETS_ID` | - | No | ID del spreadsheet |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | - | No | Credentials de Google Cloud (contenido o path) |
| `ENV` | development | No | development / production |
| `WEBHOOK_URL` | - | No | Solo producción |
| `WEBHOOK_PORT` | 8080 | No | Solo producción |

---

## 8. Setup Google Sheets API (Instrucciones)

### Paso 1: Crear proyecto en Google Cloud Console
1. Ir a https://console.cloud.google.com/
2. Crear nuevo proyecto (nombre: `cryptospy`)
3. Habilitar la API: **Google Sheets API** y **Google Drive API**

### Paso 2: Crear Service Account
1. Ir a `IAM & Admin` → `Service Accounts`
2. Crear cuenta de servicio: `cryptospy-bot@...`
3. Generar clave JSON y descargarla
4. Guardar el contenido JSON en la variable `GOOGLE_SERVICE_ACCOUNT_JSON`

### Paso 3: Compartir el Spreadsheet
1. Crear hoja de cálculo vacía en Google Sheets
2. Compartir con el email del service account (lector y editor)
3. Copiar el ID del spreadsheet de la URL:
   `https://docs.google.com/spreadsheets/d/{ESTE_ES_EL_ID}/edit`
4. Guardar en `GOOGLE_SHEETS_ID`

---

## 9. Estrategia de Deploy

### Fase 1: Desarrollo Local
- Polling mode (`ENV=development`)
- Scheduler funciona en background con APScheduler
- Google Sheets con service account real
- Grok API con key real
- `.env` local con todas las variables

### Fase 2: Producción (Fly.io)
- Webhook mode (`ENV=production`)
- Mismas variables pasadas como `fly secrets`
- Scheduler sigue funcionando en background (misma VM)
- Google Sheets sigue siendo el mismo spreadsheet (compartido)

### Por qué una sola VM en Fly.io es suficiente
- El scheduler de APScheduler corre en el mismo proceso async del bot.
- No se necesita worker separado ni Redis para este caso (solo 1 usuario, 1 mes de prueba).
- Si en el futuro se escala, se migraría a Redis + Celery o similar.

---

## 10. Decisiones de Diseño Pendientes

| # | Decisión | Estado |
|---|----------|--------|
| 1 | ¿CoinGecko free tier es suficiente o se necesita pro API? | Pendiente (free tiene rate limit 10-30 calls/min) |
| 2 | ¿Se necesita fallback de precios (Binance como backup)? | Pendiente |
| 3 | ¿El bot envía notificación automática al generar señales o solo al verificar? | Pendiente |
| 4 | ¿Qué pasa si Grok devuelve JSON malformado? | Pendiente (retry + log) |
| 5 | ¿Se guarda el JSON completo de Grok en algún lado (logs/S3)? | Pendiente |

---

## 11. Diagrama de Arquitectura (Texto)

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Telegram      │────▶│  CryptoSpy   │────▶│  Grok API (xAI) │
│   (Usuario)     │◄────│     Bot      │◄────│  + X/Twitter    │
└─────────────────┘     └──────┬───────┘     └─────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌──────────┐    ┌──────────┐    ┌──────────────┐
        │ APSched  │    │ CoinGecko│    │ Google Sheets│
        │ (timer)  │    │ (precios)│    │ (persistencia)│
        └──────────┘    └──────────┘    └──────────────┘
```

---

## 12. Notas de Implementación

- El bot usa **una sola VM** (Fly.io hobby) con todo corriendo en el mismo proceso.
- El scheduler de APScheduler usa `AsyncIOScheduler` para no bloquear el event loop del bot.
- Cada señal tiene un `signal_id` único generado por el bot (`{timestamp}_{rank}`).
- Las tareas de verificación se programan individualmente por señal, no en batch.
- Si el bot se reinicia, las tareas programadas en memoria se pierden. **Mitigación**: al arrancar, el bot lee todas las filas con `status=PENDING` del spreadsheet y re-programa las verificaciones faltantes.
