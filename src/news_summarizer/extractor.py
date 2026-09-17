from __future__ import annotations

import html
import ipaddress
import socket
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlparse


MAX_DOWNLOAD = 2 * 1024 * 1024


@dataclass(frozen=True)
class Article:
    url: str
    title: str
    text: str
    author: str | None = None
    published: str | None = None


class ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.paragraphs: list[str] = []
        self.metadata: dict[str, str] = {}
        self._capture_title = False
        self._paragraph_depth = 0
        self._ignored_depth = 0
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag in {"script", "style", "nav", "footer", "svg", "noscript"}:
            self._ignored_depth += 1
        if self._ignored_depth:
            return
        if tag == "title":
            self._capture_title = True
        if tag == "p":
            self._paragraph_depth += 1
            if self._paragraph_depth == 1:
                self._buffer = []
        if tag == "meta":
            key = (attributes.get("property") or attributes.get("name") or "").lower()
            content = attributes.get("content")
            if key and content:
                self.metadata[key] = content.strip()

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav", "footer", "svg", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if self._ignored_depth:
            return
        if tag == "title":
            self._capture_title = False
        if tag == "p" and self._paragraph_depth:
            self._paragraph_depth -= 1
            if self._paragraph_depth == 0:
                paragraph = " ".join("".join(self._buffer).split())
                if len(paragraph) >= 30:
                    self.paragraphs.append(paragraph)
                self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        if self._capture_title:
            self.title_parts.append(data)
        if self._paragraph_depth:
            self._buffer.append(data)


def _validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("URL must be a public HTTP(S) address without credentials")
    if parsed.hostname.lower() == "localhost":
        raise ValueError("Local addresses are not allowed")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443)}
    except socket.gaierror as exc:
        raise ValueError("Hostname could not be resolved") from exc
    if not addresses:
        raise ValueError("Hostname has no usable addresses")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("Private, loopback, and reserved addresses are not allowed")


def parse_article(html_text: str, url: str) -> Article:
    parser = ArticleParser()
    parser.feed(html_text)
    title = (
        parser.metadata.get("og:title")
        or parser.metadata.get("twitter:title")
        or " ".join("".join(parser.title_parts).split())
        or "Untitled article"
    )
    author = parser.metadata.get("author") or parser.metadata.get("article:author")
    published = parser.metadata.get("article:published_time") or parser.metadata.get("date")
    return Article(
        url=url,
        title=html.unescape(title),
        text="\n\n".join(parser.paragraphs),
        author=author,
        published=published,
    )


class PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject disallowed destinations before urllib issues the redirect request."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def extract_article(url: str, timeout: float = 10.0) -> Article:
    _validate_public_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "NewsSummarizer/0.1 (+https://github.com/mrsddq)"})
    # Do not inherit an ambient proxy that could resolve destinations differently.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), PublicRedirectHandler())
    with opener.open(request, timeout=timeout) as response:
        final_url = response.geturl()
        _validate_public_url(final_url)
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError(f"Expected HTML, received {content_type}")
        data = response.read(MAX_DOWNLOAD + 1)
        if len(data) > MAX_DOWNLOAD:
            raise ValueError("Article is larger than 2 MB")
        charset = response.headers.get_content_charset() or "utf-8"
    article = parse_article(data.decode(charset, errors="replace"), final_url)
    if len(article.text) < 100:
        raise ValueError("Page did not contain enough article text")
    return article

