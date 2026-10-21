import argparse
from typing import TypedDict

from src.constants import (
    DEFAULT_DOWNLOAD_PATH,
    DEFAULT_MAX_LEVEL,
    DEBUG,
    LEVEL,
    PATH,
    RECURSIVE,
    RUN_TESTS,
    URL,
)


class Options(TypedDict):
    url: str | None
    recursive: bool
    level: int
    path: str
    debug: bool
    run_tests: bool


def argument_manager() -> Options:
    parser = argparse.ArgumentParser()
    parser.add_argument(URL, type=str, nargs="?", help="The URL to scrape")
    parser.add_argument(
        "-t",
        "--run_tests",
        action="store_true",
        help="Run tests for the program",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recursively download images from the URL",
    )
    parser.add_argument(
        "-l",
        "--level",
        type=int,
        help=f"Maximum recursive download depth (default: {DEFAULT_MAX_LEVEL})"
    )
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        help=f"Download path (default: {DEFAULT_DOWNLOAD_PATH})",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activate verbose debug logging",
    )

    args = parser.parse_args()

    if not args.url and not args.run_tests:
        parser.error(
            "You must either provide a valid URL or run tests with --run_tests"
        )

    options: Options = {
        URL: args.url,
        RECURSIVE: args.recursive,
        LEVEL: (
            args.level
            if args.level is not None
            else DEFAULT_MAX_LEVEL
        ),
        PATH: args.path or DEFAULT_DOWNLOAD_PATH,
        DEBUG: args.debug,
        RUN_TESTS: args.run_tests,
    }
    return options
