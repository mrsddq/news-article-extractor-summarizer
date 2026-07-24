# News Article Extractor + Summarizer

Turn a news URL into clean article text, metadata, and a concise extractive summary. The service uses only local Python processing and includes SSRF-focused URL checks for safer server deployment.

## Features

- Extracts title, author, publication date, and article paragraphs
- Removes scripts, styles, navigation, and other common boilerplate
- Ranks original sentences using keyword frequency and lead position
- Blocks local, private, reserved, credentialed, and non-HTTP URLs
- Enforces timeouts, content types, download size, and summary length

## Run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn news_summarizer.api:app --reload
```

```bash
curl -X POST http://localhost:8000/v1/extract \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/news/story","sentences":3}'

news-summary https://example.com/news/story --sentences 3
```

The API response contains `title`, `author`, `published`, `summary`, `text`, and `word_count`.

## Security

The fetcher resolves and rejects non-global IP addresses before each request and after redirects. In high-risk deployments, also enforce egress policy at the network layer because DNS rebinding cannot be eliminated entirely in application code.

```bash
pytest
ruff check .
docker build -t news-summarizer .
```

MIT licensed.
