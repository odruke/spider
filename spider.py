#!/usr/bin/env python3

import logging
import subprocess
import sys
import os
from pathlib import Path

from src.constants import LEVEL, PATH, URL, RECURSIVE, DEBUG, RUN_TESTS, \
    EXIT, RUN_SCORPION, SCORPION_EXEC, SCORPION_PATH, MAX_LINKS, \
    SCORPION_INTERPRETER, RUN_SC_CLI, RUN_SC_GUI
from scraper.Crawler import Crawler
from src.tools import is_valid_url, setup_logger, run_menu, validate_scorpion
from src.arguments_manager import argument_manager

logger = logging.getLogger(__name__)


def main():
    options = argument_manager()

    if options[RUN_TESTS]:
        return subprocess.run([sys.executable, "-m", "pytest"])

    setup_logger(options[DEBUG])

    url = options[URL]

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
    else:
        if not validate_scorpion():
            return

        if len(downloaded_images) < 1:
            logger.info("Can't browse any image. no images were downloaded")
            return
        if choice == RUN_SC_CLI:
            args = [str(SCORPION_INTERPRETER), str(SCORPION_EXEC)]
        elif choice == RUN_SC_GUI:
            args = [str(SCORPION_INTERPRETER), str(SCORPION_EXEC), "--gui"]

        for img_path in downloaded_images:
            path = Path(img_path).resolve()
            rel_img_path = os.path.relpath(path, SCORPION_PATH)
            args.append(rel_img_path)
        return subprocess.run(args, cwd=SCORPION_PATH)


if __name__ == "__main__":
    main()
