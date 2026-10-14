from src.tools import is_valid_url


def test_accepts_http_url():
    assert is_valid_url("https://example.com/products") is True


def test_rejects_invalid_scheme():
    assert is_valid_url("ftp://example.com/file") is False


def test_rejects_localhost():
    assert is_valid_url("http://localhost:8000") is False


def test_rejects_missing_host():
    assert is_valid_url("https:///missing-host") is False
