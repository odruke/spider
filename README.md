*This project has been created as part of the 42 curriculum by odruke-s.*

# Spider

Spider is a command-line image crawler for the Arachnida project. It
downloads images found in an HTTP or HTTPS page and can optionally follow
links on the same host. After the crawl, it can pass the downloaded image
paths to the companion Scorpion program for image metadata analysis.

The program is intentionally bounded. It validates URLs, applies robots.txt
rules, restricts requests to the original scheme, host, and port, limits the
number and size of downloads, and does not follow HTTP redirects.

## Features

- Crawl one user-provided HTTP or HTTPS URL.
- Extract images from HTML `<img src="...">` elements.
- Resolve relative image and link URLs with `urllib.parse.urljoin`.
- Optionally follow links recursively on the original scheme, hostname, and
  port.
- Respect the target site's `robots.txt` rules when they are available.
- Reject unsafe image filenames and unsupported image extensions.
- Stream downloads through temporary `.part` files and keep only completed
  files.
- Launch Scorpion in either CLI or GUI mode after downloading images.
- Run the project's pytest suite with `--run_tests`.

## Requirements

- Python 3.12 or a compatible Python 3 release.
- Network access to the target URL.
- A terminal that supports Python's `curses` interface.
- The dependencies listed in [`requirements.txt`](requirements.txt).
- A usable Scorpion checkout in the sibling `../scorpion` directory if
  Scorpion analysis is required.

Spider uses a Scorpion interpreter at
`../scorpion/.venv/bin/python` and a Scorpion entry point at
`../scorpion/scorpion.py`. The paths are derived from the repository layout;
they are not command-line options.

## Installation

From the Spider project directory, create a local virtual environment and
install the dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The repository may contain a local virtual environment, but virtual
environments should be created locally and should not be copied between
machines.

## Usage

Run Spider from the project root:

```bash
python spider.py URL [options]
```

Examples:

```bash
# Crawl one page and save images under ./data
python spider.py https://example.com

# Follow links on the same host up to the configured recursion level
python spider.py https://example.com -r

# Set the maximum recursion depth and output directory
python spider.py https://example.com -r -l 3 -p ./downloads

# Enable debug logging
python spider.py https://example.com --debug

# Run the tests instead of starting a crawl
python spider.py --run_tests
```

### Command-line options

| Option | Description |
| --- | --- |
| `URL` | Optional positional URL. It must use `http` or `https` and include a host. It is required unless `--run_tests` is used. |
| `-r`, `--recursive` | Follow links found in successfully retrieved HTML pages. |
| `-l`, `--level LEVEL` | Maximum recursion depth. The default is `5`. |
| `-p`, `--path PATH` | Directory for downloaded images. The default is `./data`. The directory is created when necessary. |
| `--debug` | Enable debug-level logging. |
| `-t`, `--run_tests` | Run pytest and do not start the crawler. |

The crawler has an internal maximum of 50 visited links and 20 downloaded
images. These limits are constants in [`src/constants.py`](src/constants.py)
and are not currently command-line options.

## Crawl behavior and protections

### URL scope

The initial URL must use HTTP or HTTPS and must not use `localhost`. Links and
images are accepted only when their normalized scheme, hostname, and port
match the initial URL. External hosts, different schemes, and different ports
are skipped.

The crawler does not currently enforce the initial URL's path as a separate
scope restriction. A same-host link outside the initial path can therefore be
considered, subject to the other checks and crawl limits.

### robots.txt

Before crawling, Spider requests `/robots.txt` for the initial scheme, host,
and port using the user agent:

```text
Arachnida42/1.0 (contact: odruke-s@student.42lausanne.ch) requests
```

Behavior is status-dependent:

- `200`: parse the returned rules and use them for link and image checks.
- `404`: allow crawling because no robots file was found.
- `401` or `403`: disallow crawling and image requests.
- Other server errors: retry up to three times, then allow crawling if the
  rules could not be retrieved.
- Request or parsing failures: log the failure and allow crawling when no
  usable rules are available.

Robots exclusion rules are an important courtesy mechanism, not a security
boundary. A website can block, throttle, challenge, or otherwise reject
requests independently of robots.txt.

### Requests, redirects, and response limits

- Page and image requests use connect/read timeouts of 5 and 15 seconds.
- The robots.txt request uses a 10-second timeout.
- The crawler waits for the configured robots crawl delay, or one second when
  no delay is provided.
- HTTP redirects are disabled for page and image requests. A redirect
  response is treated as an unsuccessful request; Spider does not follow the
  `Location` header.
- Pages must return status `200`.
- If a page supplies a `Content-Type`, it must be HTML.
- Page responses are limited to 20 MiB.
- Images must advertise an `image/*` content type and are limited to 50 MiB.
- Downloads are streamed in 8 KiB chunks.
- Incomplete image downloads are removed from their `.part` files.

These checks reduce accidental resource consumption, but they do not provide
complete protection against hostile servers, malicious HTML, resource
exhaustion outside the configured limits, or all forms of network abuse.

### Image filename and extension checks

Image names are taken from the URL path, percent-decoded, lowercased, and
validated before writing. The accepted extensions are:

```text
jpg, jpeg, png, gif, bmp
```

Names containing unsafe characters, path traversal components, control
characters, or an empty basename are skipped. The file name also includes a
short SHA-256 identifier of the image URL and a timestamp to reduce
collisions.

## Output and Scorpion integration

Downloaded images are written to the selected directory. Spider does not
produce site maps, product records, or extractor-specific text files.

After crawling, a `curses` menu asks whether to:

- exit;
- launch Scorpion in CLI mode; or
- launch Scorpion with its `--gui` option.

If no images were downloaded, Scorpion is not launched. Before launching,
Spider verifies that the Scorpion script exists and is executable and that
the expected Scorpion Python interpreter exists. Failures are logged and the
program returns without changing the process exit status.

## Project structure

```text
spider/
├── spider.py
├── requirements.txt
├── README.md
├── src/
│   ├── __init__.py
│   ├── arguments_manager.py
│   ├── constants.py
│   ├── menu.py
│   └── tools.py
├── scraper/
│   ├── __init__.py
│   └── Crawler.py
└── tests/
    ├── test_Crawler.py
    └── test_tools.py
```

- [`spider.py`](spider.py): command-line entry point and crawl/Scorpion
  orchestration.
- [`src/arguments_manager.py`](src/arguments_manager.py): command-line
  parsing and default values.
- [`src/constants.py`](src/constants.py): menu values, limits, timeouts,
  paths, and crawler configuration.
- [`src/menu.py`](src/menu.py): `curses` menu and selection handling.
- [`src/tools.py`](src/tools.py): URL validation, logging setup, and Scorpion
  validation.
- [`scraper/Crawler.py`](scraper/Crawler.py): robots.txt handling, page
  crawling, link filtering, image validation, and image downloads.
- [`tests/test_Crawler.py`](tests/test_Crawler.py): crawler and image download
  tests.
- [`tests/test_tools.py`](tests/test_tools.py): URL validation tests.

## Testing

Run the complete test suite:

```bash
python -m pytest
```

The tests use mocked responses and do not require network access.

## Responsible use and limitations

Only crawl sites and resources that you are authorized to access. Respect the
site's terms of service, robots.txt directives, rate limits, and applicable
law. Spider does not implement authentication, JavaScript execution, browser
automation, CAPTCHA handling, proxy rotation, robots.txt policy negotiation,
or adaptive server-rate-limit handling.

The crawler parses server-returned HTML with Beautiful Soup. It does not
execute JavaScript, so images inserted dynamically by client-side code will
not be discovered. It also does not retry ordinary page or image requests,
follow redirects, verify image file signatures beyond the response content
type, or provide a resumable download mechanism.

## AI-use disclaimer

AI tools were used during development to assist with code review, identify
maintainability and error-handling concerns, improve documentation, and
suggest targeted code changes. The repository code, project decisions, and
final changes remain the responsibility of the project author. AI-generated
suggestions were reviewed against the source code, tests, and documented
behavior; AI assistance does not replace manual review, testing, or the
author's responsibility to understand and validate the implementation.

## References

- [Python documentation](https://docs.python.org/3/)
- [Python `curses` documentation](https://docs.python.org/3/library/curses.html)
- [Requests documentation](https://requests.readthedocs.io/en/latest/)
- [Beautiful Soup documentation](https://beautiful-soup-4.readthedocs.io/en/latest/)
- [Python `urllib.parse` documentation](https://docs.python.org/3/library/urllib.parse.html)
- [RFC 9309: Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309)
