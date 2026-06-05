import logging
import sys


class ColoredFormatter(logging.Formatter):
    """Formatter simple con colores ANSI para consola."""

    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{color}{self.BOLD}{record.levelname:<8}{self.RESET}"
        return super().format(record)


def setup_logging():
    """Configura logging claro con colores para la consola."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ColoredFormatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
    )
