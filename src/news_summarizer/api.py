from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from .extractor import extract_article
from .summarizer import summarize


app = FastAPI(title="News Article Extractor + Summarizer", version="0.1.0")


class ExtractRequest(BaseModel):
    url: HttpUrl
    sentences: int = Field(default=3, ge=1, le=10)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/extract")
def extract(request: ExtractRequest) -> dict[str, object]:
    try:
        article = extract_article(str(request.url))
        summary = summarize(article.text, request.sentences)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "Could not fetch article from the upstream source") from exc
    return {
        "url": article.url,
        "title": article.title,
        "author": article.author,
        "published": article.published,
        "summary": summary,
        "text": article.text,
        "word_count": len(article.text.split()),
    }

