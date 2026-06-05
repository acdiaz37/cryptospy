import asyncio
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from config import settings
from bot.handlers import start, analyze_command, status_command, settings_command, history_command, callback_router
from bot.scheduler import BotScheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Callback ejecutado después de que la app está lista."""
    scheduler = BotScheduler(application)
    application.bot_data["scheduler"] = scheduler
    scheduler.start()
    logger.info("Bot post_init complete. Scheduler started.")


async def post_shutdown(application: Application) -> None:
    """Callback ejecutado antes de apagar."""
    scheduler: BotScheduler = application.bot_data.get("scheduler")
    if scheduler:
        scheduler.scheduler.shutdown(wait=False)
        logger.info("Scheduler shutdown.")


def main() -> None:
    application = (
        Application.builder()
        .token(settings.BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CallbackQueryHandler(callback_router))

    if settings.ENV == "development":
        logger.info("Modo: POLLING (desarrollo)")
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    else:
        logger.info("Modo: WEBHOOK (producción)")
        application.run_webhook(
            listen="0.0.0.0",
            port=settings.WEBHOOK_PORT,
            webhook_url=settings.WEBHOOK_URL,
            drop_pending_updates=True,
        )


if __name__ == "__main__":
    main()
