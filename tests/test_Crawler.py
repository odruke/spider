from pathlib import Path

import pytest
import requests
from bs4 import BeautifulSoup

from scraper.Crawler import Crawler


class FakeResponse:
    def __init__(
            self,
            chunks=(),
            status_code=200,
            content_type="image/jpeg"
            ):
        self.status_code = status_code
        self.headers = {"content-type": content_type}
        self._chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def iter_content(self, chunk_size):
        return iter(self._chunks)


def make_crawler(tmp_path: Path) -> Crawler:
    return Crawler(
        "https://example.com/shop/index.html",
        str(tmp_path / "images"),
        recursivity=False,
        links_max=10,
        max_level=1,
    )


def test_crawler_follows_allowed_links(tmp_path, monkeypatch):
    pages = {
        "https://example.com/shop/index.html": """
            <a href="/shop/item-1">Item 1</a>
            <a href="https://other.com/page">External</a>
        """,
        "https://example.com/shop/item-1": "<h1>Item 1</h1>",
    }

    crawler = Crawler(
        "https://example.com/shop/index.html",
        str(tmp_path / "images"),
        recursivity=True,
        links_max=10,
        max_level=2,
    )

    monkeypatch.setattr(
        crawler,
        "_Crawler__get_site",
        lambda url: pages[url],
    )

    crawler.scrape()

    assert crawler.visited == {
        "https://example.com/shop/index.html",
        "https://example.com/shop/item-1",
    }


def test_crawler_respects_link_limit(tmp_path, monkeypatch):
    crawler = Crawler(
        "https://example.com/shop/index.html",
        str(tmp_path / "images"),
        recursivity=True,
        links_max=1,
        max_level=2,
    )

    monkeypatch.setattr(
        crawler,
        "_Crawler__get_site",
        lambda url: '<a href="/shop/item-1">Item</a>',
    )

    crawler.scrape()

    assert len(crawler.visited) == 1


def test_scrape_does_not_follow_links_when_non_recursive(
        tmp_path, monkeypatch
        ):
    crawler = make_crawler(tmp_path)

    monkeypatch.setattr(
        crawler,
        "_Crawler__get_site",
        lambda url: '<a href="/shop/item-1">Item</a>',
    )

    crawler.scrape()

    assert crawler.visited == {"https://example.com/shop/index.html"}


def test_get_image_name_extracts_and_normalizes_filename(tmp_path):
    crawler = make_crawler(tmp_path)

    get_image_name = crawler._Crawler__get_image_name

    assert get_image_name(
        "https://example.com/images/My%20Photo.JPG?size=large"
    ) == "my photo.jpg"


@pytest.mark.parametrize(
    "src",
    [
        "",
        "/images/",
        "/images/..",
        "/images/photo%00.jpg",
        "/images/photo%0a.jpg",
        "/images/photo%5cname.jpg",
        "/images/photo:name.jpg",
        "/images/.jpg",
    ],
)
def test_get_image_name_rejects_unsafe_or_empty_names(tmp_path, src):
    crawler = make_crawler(tmp_path)

    assert crawler._Crawler__get_image_name(src) == ""


def test_image_extractor_downloads_allowed_relative_image(
        tmp_path, monkeypatch
        ):
    crawler = make_crawler(tmp_path)
    requested_urls = []

    def fake_get(url, **kwargs):
        requested_urls.append((url, kwargs))
        return FakeResponse([b"image-bytes"], content_type="image/png")

    monkeypatch.setattr(requests, "get", fake_get)

    soup = BeautifulSoup(
        '<img src="/images/photo.PNG?version=1">',
        "html.parser",
    )

    crawler._Crawler__image_extractor(
        "https://example.com/shop/index.html",
        soup,
    )

    files = list((tmp_path / "images").glob("*"))
    assert len(files) == 1
    assert files[0].name.endswith("_photo.png")
    assert files[0].read_bytes() == b"image-bytes"
    assert requested_urls == [
        (
            "https://example.com/images/photo.PNG?version=1",
            {
                "timeout": (5, 15),
                "allow_redirects": False,
                "stream": True,
            },
        )
    ]


def test_image_extractor_skips_missing_unsafe_and_external_images(
        tmp_path, monkeypatch
        ):
    crawler = make_crawler(tmp_path)
    requested_urls = []

    def fake_get(url, **kwargs):
        requested_urls.append(url)
        return FakeResponse([b"image-bytes"])

    monkeypatch.setattr(requests, "get", fake_get)

    soup = BeautifulSoup(
        """
        <img>
        <img src="">
        <img src="/images/photo.txt">
        <img src="/images/photo%00.jpg">
        <img src="https://other.example/photo.jpg">
        """,
        "html.parser",
    )

    crawler._Crawler__image_extractor(
        "https://example.com/shop/index.html",
        soup,
    )

    assert requested_urls == []
    assert list((tmp_path / "images").iterdir()) == []


def test_image_extractor_continues_after_failed_image(
        tmp_path, monkeypatch
        ):
    crawler = make_crawler(tmp_path)
    requested_urls = []

    def fake_get(url, **kwargs):
        requested_urls.append(url)
        if url.endswith("/broken.jpg"):
            raise requests.ConnectionError("connection failed")
        return FakeResponse([b"valid-image"], content_type="image/jpeg")

    monkeypatch.setattr(requests, "get", fake_get)

    soup = BeautifulSoup(
        """
        <img src="/images/broken.jpg">
        <img src="/images/valid.jpg">
        """,
        "html.parser",
    )

    crawler._Crawler__image_extractor(
        "https://example.com/shop/index.html",
        soup,
    )

    files = list((tmp_path / "images").glob("*"))
    assert requested_urls == [
        "https://example.com/images/broken.jpg",
        "https://example.com/images/valid.jpg",
    ]
    assert len(files) == 1
    assert files[0].name.endswith("_valid.jpg")
    assert files[0].read_bytes() == b"valid-image"


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse([b"not-an-image"], status_code=404),
        FakeResponse([b"html"], content_type="text/html"),
        FakeResponse([b"unknown"], content_type=None),
    ],
)
def test_image_extractor_does_not_save_invalid_responses(
        tmp_path, monkeypatch, response
        ):
    crawler = make_crawler(tmp_path)

    monkeypatch.setattr(requests, "get", lambda url, **kwargs: response)

    soup = BeautifulSoup(
        '<img src="/images/photo.jpg">',
        "html.parser",
    )

    crawler._Crawler__image_extractor(
        "https://example.com/shop/index.html",
        soup,
    )

    assert list((tmp_path / "images").iterdir()) == []
    assert list((tmp_path / "images").glob("*.part")) == []
