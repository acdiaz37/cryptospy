import logging
import re

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from config import settings
from core.logger import setup_logging
from bot.handlers import start, analyze_command, status_command, settings_command, history_command, callback_router, help_command
from bot.scheduler import BotScheduler


class TokenFilter(logging.Filter):
    """Ofusca el BOT_TOKEN de los logs."""

    def filter(self, record):
        if hasattr(record, "msg") and isinstance(record.msg, str):
            record.msg = re.sub(r"bot\d+:[A-Za-z0-9_-]{35}", "bot***:***", record.msg)
        if hasattr(record, "args"):
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    new_args.append(re.sub(r"bot\d+:[A-Za-z0-9_-]{35}", "bot***:***", arg))
                else:
                    new_args.append(arg)
            record.args = tuple(new_args)
        return True


setup_logging()

# Silenciar logs de httpx que exponen URLs con token
logging.getLogger("httpx").setLevel(logging.WARNING)

# Aplicar filtro de token a loggers relevantes
for logger_name in ("telegram.ext.Application", "httpx", "__main__"):
    logging.getLogger(logger_name).addFilter(TokenFilter())

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Callback ejecutado después de que la app está lista."""
    scheduler = BotScheduler(application)
    application.bot_data["scheduler"] = scheduler
    scheduler.start()
    logger.info("[bold green]Bot post_init complete. Scheduler started.[/bold green]")


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
    application.add_handler(CommandHandler("help", help_command))
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
