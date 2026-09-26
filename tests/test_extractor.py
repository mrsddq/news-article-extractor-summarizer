import pytest

from news_summarizer.extractor import _validate_public_url, parse_article
from news_summarizer.summarizer import summarize


HTML = """
<html><head><title>Fallback</title>
<meta property="og:title" content="A Test Headline">
<meta name="author" content="Ada Reporter"></head>
<body><nav><p>This navigation text should not be extracted at all.</p></nav>
<article>
<p>The city opened a new solar-powered library on Tuesday. The building can serve five hundred visitors each day.</p>
<p>Officials said the project cut expected energy use by forty percent. Residents helped design the public reading rooms.</p>
</article><script>secret()</script></body></html>
"""


def test_article_metadata_and_body_are_extracted():
    article = parse_article(HTML, "https://example.com/story")
    assert article.title == "A Test Headline"
    assert article.author == "Ada Reporter"
    assert "solar-powered library" in article.text
    assert "navigation" not in article.text


def test_summarizer_preserves_original_sentence_order():
    summary = summarize(parse_article(HTML, "https://example.com").text, 2)
    assert 1 <= summary.count(".") <= 2
    assert "library" in summary or "project" in summary


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://localhost/admin", "ftp://example.com/a"])
def test_private_or_unsupported_urls_are_rejected(url):
    with pytest.raises(ValueError):
        _validate_public_url(url)

def test_line_breaks_preserve_word_boundaries():
    article = parse_article(
        "<p>The city opened a new library.<br>Residents welcomed the project.</p>",
        "https://example.com/story",
    )
    assert article.text == "The city opened a new library. Residents welcomed the project."
