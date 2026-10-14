import logging
import re
from urllib.parse import urljoin, urlparse, unquote
import hashlib
from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup

from src.constants import MAX_RESPONSE_SIZE, CHUNK_SIZE, MAX_IMAGE_SIZE, MAX_IMAGES

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

        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.links_max = links_max
        self.max_level = max_level
        self.recursivity = recursivity
        self.visited = set()
        self.failed = set()
        self.valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp']
        self.downloaded_imgs = set()

        logger.info(f"Recursivity: {"True" if self.recursivity else "False"}")
        logger.info(f"Max fo links to search in: {self.links_max}")
        logger.info(f"Max recursion level: {self.max_level}")

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

        with requests.get(
            image_url,
            timeout=(5, 15),
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

    def __image_extractor(self, url: str, soup: BeautifulSoup):
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
        parsed = urlparse(url)
        if parsed.scheme.lower() != self.allowed_scheme:
            return False

        if parsed.hostname is None:
            return False

        if parsed.hostname.lower() != self.allowed_hostname:
            return False

        if parsed.port != self.allowed_port:
            return False

        return True

    def __get_site(self, url: str) -> str:

        with requests.get(
            url,
            timeout=(5, 15),
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

    def __crawl(self, url: str, max_level: int):
        if max_level <= 0:
            logger.debug("Recursion reached bottom level")
            return

        if len(self.visited) >= self.links_max:
            logger.debug(f"Limit of links reached: {self.links_max}")
            return

        if len(self.downloaded_imgs) > MAX_IMAGES:
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

