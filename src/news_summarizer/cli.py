import argparse
import json

from .extractor import extract_article
from .summarizer import summarize


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract and summarize a news article")
    parser.add_argument("url")
    parser.add_argument("--sentences", type=int, default=3)
    args = parser.parse_args()
    article = extract_article(args.url)
    print(json.dumps({
        "title": article.title,
        "author": article.author,
        "published": article.published,
        "summary": summarize(article.text, args.sentences),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

