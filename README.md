# Scraper Practice

## Description

Scraper Practice is a Python command-line web scraper and site mapper. Its goal is to practice controlled web crawling, HTML parsing, site-specific data extraction, and file-based result generation.

The program uses a terminal menu to select a configured site, choose an operation, and set crawl limits. It currently supports `testingurl.dev` through `TestingurlExtractor`, which identifies product pages and extracts their name, price, rating, stock, and description. The crawler follows links within the configured site and base path, while applying recursion-depth, link-count, timeout, response-type, and response-size limits.

The two available operations are:

- **Map site:** collect the successfully visited URLs.
- **Extract products:** collect product data from matching pages and write it to text files.

### Project structure

- `main.py`: application entry point and workflow orchestration.
- `menu.py`: terminal menu implementation using `curses`.
- `tools.py`: URL validation, menu execution, and logging setup.
- `constants.py`: menu values, site configuration, and crawler limits.
- `scraper/Crawler.py`: bounded recursive crawler and link filtering.
- `scraper/extractors/ExtractorBase.py`: abstract contract for site extractors.
- `scraper/extractors/TestingurlExtractor.py`: extractor for `testingurl.dev` product pages.
- `scraper/extractors/testingurl_urls.txt`: seed URLs processed by the program.
- `extracted_data/`: product extraction output.
- `site_maps/`: site map output.

## Instructions

### Requirements

- Python 3.12 or a compatible Python 3 release.
- A terminal that supports the Python `curses` interface.
- Network access to the URLs listed in `scraper/extractors/testingurl_urls.txt`.

The project includes a virtual environment configured with Python 3.12.3, but virtual environments should generally be created locally rather than committed or copied between machines.

### Installation

From the project root, create and activate a virtual environment:

```bash
python3.12 -m venv env
source env/bin/activate
```

Install the project dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Execution

Run the application from the project root:

```bash
python main.py
```

Use the keyboard to navigate the menus:

1. Select the configured site, or select `Exit`.
2. Select `Map site` or `Extract products`.
3. Select the maximum recursion level.
4. Select the maximum number of links to crawl.
5. Confirm each menu choice with `Enter`.

The input URLs are read from `scraper/extractors/testingurl_urls.txt`, one URL per line. Invalid URLs are skipped. The program waits the configured delay between source URLs.

### Output

Product extraction results are written to `extracted_data/` using filenames that include the extractor domain, a short SHA-256 identifier of the source URL, and a timestamp.

Site map results are written to `site_maps/` using the same naming strategy. Existing files are not reused when a new timestamp is generated.

### Adding another extractor

To add support for another site:

1. Create a class derived from `ExtractorBase` in `scraper/extractors/`.
2. Initialize its `urls_file`, `base_path`, and `domain` values.
3. Implement `extract_element(soup, url)` to return site-specific structured data.
4. Implement `write_element(element)` to serialize one extracted result.
5. Add the site constant and factory selection in `constants.py` and `ExtractorFactory.py`.
6. Add the site and its menu entry in `menu.py` if required.
7. Add seed URLs in the extractor's URL file.


### Current limitations

- Only `testingurl.dev` is registered in the extractor factory.
- JavaScript-rendered content is not executed; the crawler parses the server response with Beautiful Soup.
- Redirects are currently disabled.
- Crawling is restricted to the initial scheme, hostname, port, and base path.
- Each response is limited to 20 MiB and must be an HTML response when a content type is provided.
- The crawler does not currently implement robots.txt handling or per-domain rate-limit negotiation. Users should only crawl sites they are authorized to access and should respect the target site's policies.

## Resources

- [Python Documentation](https://docs.python.org/3/): language reference and standard-library documentation.
- [Python `venv` Documentation](https://docs.python.org/3/library/venv.html): creating isolated Python environments.
- [Python `curses` Documentation](https://docs.python.org/3/library/curses.html): terminal user-interface support used by the menus.
- [Requests Documentation](https://requests.readthedocs.io/en/latest/): HTTP requests, timeouts, and response handling.
- [Beautiful Soup Documentation](https://beautiful-soup-4.readthedocs.io/en/latest/): HTML parsing and document navigation.
- [Python `urllib.parse` Documentation](https://docs.python.org/3/library/urllib.parse.html): URL parsing and joining used by the crawler.
- [Flake8 Documentation](https://flake8.pycqa.org/en/latest/): Python style and static-analysis checks.
- [RFC 9309 - Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309): standard reference for robots.txt behavior and crawler responsibilities.

### AI use

AI assisted with the project code review, identification of security and maintainability concerns, addition of focused Python docstrings, and preparation of this README. The implementation and repository-specific instructions were based on the existing project files and were reviewed against the current code structure.
