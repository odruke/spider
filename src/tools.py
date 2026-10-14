import curses
import logging
from urllib.parse import urlparse
import os

from src.menu import menu
from src.constants import SCORPION_EXEC, SCORPION_INTERPRETER

logger = logging.getLogger(__name__)


def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return False

    if parsed.hostname == "localhost":
        return False

    return bool(parsed.scheme and parsed.netloc)


def run_menu(options: str) -> str:
    return curses.wrapper(lambda stdscr: menu(stdscr, options))


def setup_logger(debug: bool) -> None:
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(levelname)s: %(message)s [%(filename)s:%(lineno)d]"
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
        )


def validate_scorpion() -> bool:
    if not os.path.exists(SCORPION_EXEC):
        logger.warning(f"Can't find executable {SCORPION_EXEC}")
        return False

    if not os.access(SCORPION_EXEC, os.X_OK):
        logger.warning(f"{SCORPION_EXEC} is not an executable file")
        return False

    if not SCORPION_INTERPRETER.is_file():
        logger.error("Scorpion Python interpreter not found")
        return

    return True
