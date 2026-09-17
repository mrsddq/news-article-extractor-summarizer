from email.message import Message
from unittest.mock import Mock
import urllib.request

import pytest
from fastapi.testclient import TestClient

from news_summarizer import api, extractor


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fc00::1"])
def test_dns_resolution_rejects_nonpublic_addresses(monkeypatch, address):
    monkeypatch.setattr(extractor.socket, "getaddrinfo", lambda *a: [(0, 0, 0, "", (address, 443))])
    with pytest.raises(ValueError, match="not allowed"):
        extractor._validate_public_url("https://news.example/story")


def test_redirect_is_rejected_before_creating_followup_request(monkeypatch):
    monkeypatch.setattr(extractor.socket, "getaddrinfo", lambda *a: [(0, 0, 0, "", ("127.0.0.1", 80))])
    handler = extractor.PublicRedirectHandler()
    with pytest.raises(ValueError):
        handler.redirect_request(urllib.request.Request("https://public.example"), None, 302,
                                 "Found", {}, "http://internal.example/admin")


def test_public_redirect_is_preserved(monkeypatch):
    monkeypatch.setattr(extractor.socket, "getaddrinfo", lambda *a: [(0, 0, 0, "", ("93.184.216.34", 443))])
    request = extractor.PublicRedirectHandler().redirect_request(
        urllib.request.Request("https://public.example"), None, 302, "Found", {},
        "https://other.example/article")
    assert request.full_url == "https://other.example/article"


def test_oversized_download_is_rejected_without_parsing(monkeypatch):
    monkeypatch.setattr(extractor, "_validate_public_url", lambda url: None)
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.headers = Message()
    response.headers["Content-Type"] = "text/html"
    response.read.return_value = b"a" * (extractor.MAX_DOWNLOAD + 1)
    opener = Mock()
    opener.open.return_value = response
    monkeypatch.setattr(extractor.urllib.request, "build_opener", lambda *a: opener)
    with pytest.raises(ValueError, match="larger than"):
        extractor.extract_article("https://public.example/story")
    response.read.assert_called_once_with(extractor.MAX_DOWNLOAD + 1)


def test_upstream_failure_does_not_leak_internal_details(monkeypatch):
    def broken(url):
        raise OSError("internal hostname and credential")
    monkeypatch.setattr(api, "extract_article", broken)
    response = TestClient(api.app).post("/v1/extract", json={"url": "https://example.com"})
    assert response.status_code == 502
    assert "credential" not in response.text
