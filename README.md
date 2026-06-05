# CryptoSpy Bot 🤖

Bot de Telegram para análisis de señales de trading crypto con IA (Grok/xAI) y tracking en Google Sheets.

## Flujo

1. El bot consulta precios actuales (CoinGecko)
2. Envía prompt a Grok con acceso a X/Twitter
3. Recibe señales LONG/SHORT en JSON
4. Guarda señales en Google Sheets con precio de entrada
5. Verifica automáticamente al cabo de la ventana de tiempo configurada
6. Notifica resultados por Telegram

## Stack

- `python-telegram-bot` v20+ (async)
- `httpx` (APIs externas)
- `gspread` + `google-auth` (Google Sheets)
- `apscheduler` (tareas programadas)
- Fly.io (deploy)

## Setup Local

### 1. Clonar e instalar dependencias

```bash
git clone https://github.com/acdiaz37/cryptospy.git
cd cryptospy
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Variables de entorno

Copiá el ejemplo y completá tus credenciales:

```bash
cp .env.example .env
```

Editá `.env`:

```env
BOT_TOKEN=tu_token_de_botfather
GROK_API_KEY=tu_key_de_xai
GOOGLE_SHEETS_ID=id_de_tu_spreadsheet
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
ANALYSIS_WINDOW_HOURS=24
ENV=development
```

### 3. Google Sheets API

1. Andá a [Google Cloud Console](https://console.cloud.google.com/)
2. Creá un proyecto nuevo
3. Habilitá **Google Sheets API** y **Google Drive API**
4. En `IAM & Admin` → `Service Accounts`, creá una cuenta de servicio
5. Generá una clave JSON y descargala
6. Copiá el **contenido completo del JSON** en `GOOGLE_SERVICE_ACCOUNT_JSON`
7. Creá una hoja de cálculo vacía en Google Sheets y compartila con el email de la service account (como editor)
8. Copiá el ID del spreadsheet de la URL y ponelo en `GOOGLE_SHEETS_ID`

### 4. BotFather

1. Buscá `@BotFather` en Telegram
2. Creá un bot nuevo con `/newbot`
3. Copiá el token en `BOT_TOKEN`

### 5. Ejecutar local

```bash
python main.py
```

El bot arranca en modo **polling**. Escribile `/start`.

---

## Comandos del Bot

| Comando | Descripción |
|---------|-------------|
| `/start` | Menú principal |
| `/analyze` | Ejecutar análisis manualmente |
| `/status` | Ver señales activas con P&L en vivo |
| `/settings` | Cambiar ventana de tiempo (12h/24h/48h) |
| `/history` | Últimas señales del historial |

---

## Deploy a Fly.io

### 1. Instalar Fly CLI

```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

### 2. Login y crear app

```bash
fly auth login
fly launch
```

Respondé `yes` cuando pregunte si querés copiar la config existente.

### 3. Secrets (variables sensibles)

```bash
fly secrets set BOT_TOKEN="tu_token"
fly secrets set GROK_API_KEY="tu_key"
fly secrets set GOOGLE_SHEETS_ID="tu_sheet_id"
fly secrets set GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
fly secrets set ANALYSIS_WINDOW_HOURS="24"
fly secrets set ENV="production"
fly secrets set WEBHOOK_URL="https://cryptospy-bot.fly.dev"
```

> ⚠️ En Windows PowerShell, para pasar JSON como string usá comillas simples externas.

### 4. Deploy

```bash
fly deploy
```

---

## Arquitectura

Ver `ARCHITECTURE.md` para el documento completo de diseño.

## Estructura del Proyecto

```
cryptospy/
├── bot/
│   ├── handlers.py      # Comandos y callbacks de Telegram
│   ├── keyboards.py     # Inline keyboards
│   └── scheduler.py     # APScheduler (análisis + verificación)
├── services/
│   ├── coingecko.py     # Cliente CoinGecko
│   ├── grok.py          # Cliente Grok/xAI
│   └── sheets.py        # Cliente Google Sheets
├── models/
│   └── signal.py        # Pydantic models
├── config.py            # Settings mutable
├── main.py              # Entry point
├── Dockerfile
├── fly.toml
└── requirements.txt
```
