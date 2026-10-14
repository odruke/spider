from src.constants import LEVEL, RECURSIVE, PATH, DEBUG, URL, RUN_TESTS

import argparse


def argument_manager() -> dict:
    options = {
        URL: None,
        RECURSIVE: False,
        LEVEL: 0,
        PATH: None,
        DEBUG: False,
        RUN_TESTS: False
    }

    parser = argparse.ArgumentParser()

    parser.add_argument('URL', type=str, nargs="?", help='The url to scrap')

    parser.add_argument('-t',
                        '--run_tests',
                        action='store_true',
                        help='Run test for the program')

    parser.add_argument('-r',
                        '--recursive',
                        action='store_true',
                        help='recursively downloads the images in a URL\
 received as a parameter')

    parser.add_argument('-l',
                        '--level',
                        type=int,
                        help='indicates the maximum depth level of the\
 recursive download. If not indicated, it will be 5')

    parser.add_argument('-p',
                        '--path',
                        type=str,
                        help='indicates the path where the downloaded files\
 will be saved. If not specified, ./data/ will be used.')

    parser.add_argument('--debug',
                        action='store_true',
                        help='Activates a more verbose debug log')

    args = parser.parse_args()

    if not args.URL and not args.run_tests:
        parser.error(
            "You must either provide a valid url or run tests with --tests"
                     )

    options[URL] = args.URL
    if args.recursive is not None:
        options[RECURSIVE] = args.recursive
        options[LEVEL] = args.level or 5
        options[PATH] = args.path or './data'
        options[RUN_TESTS] = args.run_tests

    options[DEBUG] = args.debug
    return options
