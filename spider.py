#!/usr/bin/env python3

import logging
import os
import subprocess
import sys
from pathlib import Path

from src.constants import (
    DEBUG,
    EXIT,
    LEVEL,
    PATH,
    RECURSIVE,
    RUN_SCORPION,
    RUN_SC_CLI,
    RUN_SC_GUI,
    RUN_TESTS,
    URL,
    MAX_LINKS,
    SCORPION_EXEC,
    SCORPION_INTERPRETER,
    SCORPION_PATH,
)
from scraper.Crawler import Crawler
from src.tools import is_valid_url, setup_logger, run_menu, validate_scorpion
from src.arguments_manager import argument_manager

logger = logging.getLogger(__name__)


def main() -> None:
    options = argument_manager()

    if options[RUN_TESTS]:
        return subprocess.run([sys.executable, "-m", "pytest"])

    setup_logger(options[DEBUG])

    url = options[URL]
    if url is None:
        logger.error("No URL was provided")
        return

    url = url.strip()
    if not is_valid_url(url):
        logger.error(f"[ {url} ] is not a valid url, closing program")
        return

    logger.info(f"crawling url: {url}")
    try:
        crawler = Crawler(
            url=url,
            recursivity=options[RECURSIVE],
            path=options[PATH],
            links_max=MAX_LINKS,
            max_level=options[LEVEL],
        )
    except (OSError, ValueError) as e:
        logger.error(f"Can't initiate crawler: {e}")
        return

    downloaded_images = crawler.scrape()

    choice = run_menu(RUN_SCORPION)

    if choice == EXIT:
        return

    if not validate_scorpion():
        return

    if not downloaded_images:
        logger.info("Can't browse any image; no images were downloaded")
        return

    if choice == RUN_SC_CLI:
        args = [str(SCORPION_INTERPRETER), str(SCORPION_EXEC)]
    elif choice == RUN_SC_GUI:
        args = [str(SCORPION_INTERPRETER), str(SCORPION_EXEC), "--gui"]
    else:
        logger.error("Unknown Scorpion menu choice: %s", choice)
        return

    for img_path in downloaded_images:
        path = Path(img_path).resolve()
        rel_img_path = os.path.relpath(path, SCORPION_PATH)
        args.append(rel_img_path)

    try:
        subprocess.run(args, cwd=SCORPION_PATH, check=False)
    except OSError as error:
        logger.error("Unable to start Scorpion: %s", error)


if __name__ == "__main__":
    main()
