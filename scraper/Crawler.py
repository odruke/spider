import logging
import hashlib
import re
from datetime import datetime
from pathlib import Path
import time
from urllib.parse import unquote, urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


from src.constants import (
    CHUNK_SIZE,
    DEFAULT_CRAWL_DELAY,
    MAX_IMAGES,
    MAX_IMAGE_SIZE,
    MAX_ROBOT_RETRIES,
    MAX_RESPONSE_SIZE,
    REQUEST_TIMEOUT,
    ROBOTS_REQUEST_TIMEOUT,
    USER_AGENT,
    VALID_IMAGE_EXTENSIONS,
)

logger = logging.getLogger(__name__)

SAFE_IMAGE_NAME = re.compile(
    r"[A-Za-z0-9](?:[A-Za-z0-9._ -]{0,253}[A-Za-z0-9])?"
)


class Crawler:
    def __init__(
            self,
            url: str,
            path: str,
            recursivity: bool,
            links_max: int,
            max_level: int
            ) -> None:
        parsed_url = urlparse(url)

        if parsed_url.scheme not in {"http", "https"}:
            raise ValueError("Only HTTP and HTTPS URLs are supported")

        if parsed_url.hostname is None:
            raise ValueError("URL  must contain a hostaname")

        self.url = url
        self.allowed_scheme = parsed_url.scheme.lower()
        self.allowed_hostname = parsed_url.hostname.lower()
        self.allowed_port = parsed_url.port
        self.allowed_path = parsed_url.path.rstrip("/") or "/"

        self.session = requests.Session()
        self.session.headers = {"User-Agent": USER_AGENT}

        self.robot = self.__get_robot()
        delay = self.robot.crawl_delay(USER_AGENT)
        self.crawl_delay = delay if delay is not None else DEFAULT_CRAWL_DELAY

        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.links_max = links_max
        self.max_level = max_level
        self.recursivity = recursivity
        self.visited = set()
        self.failed = set()
        self.valid_extensions = VALID_IMAGE_EXTENSIONS
        self.downloaded_imgs = set()

        logger.info("Recursivity: %s", self.recursivity)
        logger.info("Max of links to search in: %s", self.links_max)
        logger.info(f"Max recursion level: {self.max_level}")

    def __get_robot(self, tries: int = 0) -> RobotFileParser:
        robots = RobotFileParser()

        netloc = self.allowed_hostname

        if self.allowed_port is not None:
            netloc = f"{netloc}:{self.allowed_port}"

        robots_url = urlunparse((
            self.allowed_scheme,
            netloc,
            "/robots.txt",
            "",
            "",
            ""
        ))

        try:
            time.sleep(DEFAULT_CRAWL_DELAY)
            with self.session.get(
                robots_url,
                timeout=ROBOTS_REQUEST_TIMEOUT,
            ) as response:
                if response.status_code == 200:
                    robots.parse(response.text.splitlines())
                    logger.info("Found robots.txt, setting rules")
                    return robots
                # robots.txt not found, allow everything
                if response.status_code == 404:
                    robots.allow_all = True
                    logger.info("robots.txt not found, allowing all links")
                    return robots

                # robots.txt is forbidden, forbid everything
                if response.status_code in (401, 403):
                    robots.disallow_all = True
                    logger.warning("robots.txt is forbidden, disallowing all \
links")
                    return robots

                # server error
                if response.status_code >= 500 and tries < MAX_ROBOT_RETRIES:
                    logger.debug(
                        "Accessing robots.txt resulted in a server error; "
                        "retrying %s/%s",
                        tries + 1,
                        MAX_ROBOT_RETRIES,
                    )
                    return self.__get_robot(tries + 1)

                robots.allow_all = True
                logger.error(
                    "Error loading robots.txt (status %s), allowing all links",
                    response.status_code,
                )
                return robots

        except (requests.RequestException, OSError, ValueError) as error:
            robots.allow_all = True
            logger.error("Error loading robots.txt: %s", error)
            return robots

    def __get_image_name(self, image_src: str) -> str:
        path = urlparse(image_src).path
        if "%" in path:
            path = unquote(path)
        image_name = path.rsplit("/", 1)[-1]

        if not image_name or image_name in {".", ".."}:
            return ""

        if SAFE_IMAGE_NAME.fullmatch(image_name) is None:
            return ""

        return image_name.lower()

    def __download_img(self, image_name: str, image_url: str) -> None:
        time.sleep(self.crawl_delay)
        with self.session.get(
            image_url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
            stream=True
                ) as response:

            # for the moment, redirections are not allowed
            if response.status_code != 200:
                raise ValueError(f"Status code: {response.status_code}")

            content_length = response.headers.get("content-length")
            content_type = response.headers.get("content-type")

            if content_length is not None and content_length.isdigit():
                if int(content_length) > MAX_IMAGE_SIZE:
                    raise ValueError(f"Image too big: {content_length}")

            if content_type is None:
                raise ValueError("Can't verify if content is an image")

            if not content_type.lower().startswith("image/"):
                raise ValueError(
                    f"content-type is not an image: {content_type}"
                    )

            url_id = hashlib.sha256(image_url.encode()).hexdigest()[:12]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.path / f"{url_id}_{timestamp}_{image_name}"
            temporary_filename = filename.with_suffix(
                filename.suffix + ".part"
                )

            bytes_read = 0
            try:
                with temporary_filename.open("wb") as file:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            chunk_size = len(chunk)
                            if bytes_read + chunk_size > MAX_IMAGE_SIZE:
                                raise ValueError(
                                    f"Response too long: {bytes_read}"
                                    )

                            bytes_read += chunk_size
                            file.write(chunk)
                temporary_filename.replace(filename)
                self.downloaded_imgs.add(filename)

            except (OSError, requests.RequestException, ValueError):
                temporary_filename.unlink(missing_ok=True)
                raise

    def __image_extractor(self, url: str, soup: BeautifulSoup) -> None:
        images = soup.find_all('img')

        if len(images) < 1:
            logger.debug(f"Images not found in url: {url}")
            return

        for image in images:
            src = image.get("src")
            if src is None:
                logger.debug("Image has no src")
                continue

            image_url = urljoin(url, src)
            if not self.__is_allowed(image_url):
                logger.debug(f"Image url not allowed: {image_url}")
                continue

            image_name = self.__get_image_name(src)
            if not image_name:
                logger.debug(f"Invalid image name: {image_name}")
                continue

            extension = image_name.split('.')[-1]
            if extension not in self.valid_extensions:
                logger.debug(f"Invalid extension: {extension}")
                continue

            try:
                self.__download_img(
                    image_name=image_name,
                    image_url=image_url
                    )
            except (requests.RequestException, OSError, ValueError) as error:
                logger.warning(
                    f"Could not download image {image_url}: {error}"
                )
                continue

    def __is_allowed(self, url: str) -> bool:
        if self.robot is not None:
            if not self.robot.can_fetch(USER_AGENT, url):
                logger.debug("Blocked by robots.txt")
                return False

        parsed = urlparse(url)
        if parsed.scheme.lower() != self.allowed_scheme:
            logger.debug(f"invalid scheme: {parsed.scheme}")
            return False

        if parsed.hostname is None:
            logger.debug("No hostname")
            return False

        if parsed.hostname.lower() != self.allowed_hostname:
            logger.debug(f"Invalid hostname: {parsed.hostname}")
            return False

        if parsed.port != self.allowed_port:
            logger.debug(f"Invalid port: {parsed.port}")
            return False

        return True

    def __get_site(self, url: str) -> str:
        time.sleep(self.crawl_delay)
        with self.session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
            stream=True
                ) as response:

            # for the moment, redirections are not allowed
            if response.status_code != 200:
                raise ValueError(f"Status code: {response.status_code}")

            content_length = response.headers.get("content-length")
            content_type = response.headers.get("content-type")

            if content_length is not None and content_length.isdigit():
                if int(content_length) > MAX_RESPONSE_SIZE:
                    raise ValueError(f"Response too long: {content_length}")

            if content_type is not None:
                if "text/html" not in content_type:
                    raise ValueError(
                        f"content-type not supported: {content_type}"
                        )

            content = bytearray()

            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if not chunk:
                    continue

                content.extend(chunk)
                if len(content) > MAX_RESPONSE_SIZE:
                    raise ValueError(f"Response too long: {len(content)}")

        return content.decode(response.encoding or 'UTF-8', errors="replace")

    def __crawl(self, url: str | None, max_level: int) -> None:
        if max_level <= 0:
            logger.debug("Recursion reached bottom level")
            return

        if len(self.visited) >= self.links_max:
            logger.debug(f"Limit of links reached: {self.links_max}")
            return

        if len(self.downloaded_imgs) >= MAX_IMAGES:
            logger.info(f"Limit of downloaded images reached: {MAX_IMAGES}")
            return

        if url is None:
            logger.info("Initiating crawling")
            url = self.url

        try:
            html = self.__get_site(url)
        # except requests.exceptions.TooManyRedirects:
        # 	logger.warning(f"Redirect loop: {url}")
        # 	self.failed.add(url)
        # 	return
        except requests.RequestException as error:
            logger.warning(f"Request failed for {url}: {error}")
            self.failed.add(url)
            return
        except ValueError as e:
            logger.warning(f"Request failed for {url}: {e}")
            self.failed.add(url)
            return

        soup = BeautifulSoup(html, 'html.parser')

        logger.info(f"Extracting images from [ {url} ]")
        self.__image_extractor(url=url, soup=soup)

        self.visited.add(url)

        if not self.recursivity:
            return

        logger.info("Extracting links")
        links = [
            urljoin(url, link.get("href"))
            for link in soup.find_all('a')
            if link.get('href')
            ]

        max_level -= 1
        for link in links:
            logger.debug(f"checking link {link} in url {url}")
            if link in self.visited or link in self.failed:
                logger.debug(f"Link already visited: {link}")
                continue

            if not self.__is_allowed(link):
                self.failed.add(link)
                logger.debug(f"Link is not allowed: {link}")
                continue

            self.__crawl(url=link, max_level=max_level)

        return

    def scrape(self) -> list:
        """Recursively crawl allowed pages and collect images.

        Starting with the configured URL, this method requests HTML pages,
        limits responses by status, content type, and size, and follows links
        that remain within the same scheme, host, and port. The
        crawl stops at ``max_level`` or ``links_max`` and applies the
        configured scraping callback to every successfully downloaded page.
        """
        self.__crawl(url=self.url, max_level=self.max_level)
        return list(self.downloaded_imgs)
