import asyncio
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import settings

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"¡Hola {update.effective_user.first_name}! Soy CryptoSpy 🤖"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Comandos disponibles:\n/start - Iniciar\n/help - Ayuda"
    )


async def main() -> None:
    application = Application.builder().token(settings.BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    if settings.ENV == "development":
        logger.info("Modo: POLLING (desarrollo)")
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        await application.updater.idle()
        await application.stop()
    else:
        logger.info("Modo: WEBHOOK (producción)")
        await application.initialize()
        await application.start()
        await application.updater.start_webhook(
            listen="0.0.0.0",
            port=settings.WEBHOOK_PORT,
            webhook_url=settings.WEBHOOK_URL,
            drop_pending_updates=True,
        )
        await application.updater.idle()
        await application.stop()


if __name__ == "__main__":
    asyncio.run(main())
