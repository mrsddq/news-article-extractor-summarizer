from __future__ import annotations

import math
import re
from collections import Counter


WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]+")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
STOP_WORDS = {
    "about", "after", "again", "also", "and", "are", "because", "been", "before",
    "being", "between", "both", "but", "can", "could", "did", "does", "each", "for",
    "from", "had", "has", "have", "into", "its", "more", "most", "not", "of", "on",
    "only", "other", "our", "said", "she", "some", "such", "than", "that", "the",
    "their", "them", "there", "these", "they", "this", "through", "to", "was", "were",
    "which", "while", "who", "will", "with", "would", "you", "your",
}


def _words(text: str) -> list[str]:
    return [word.lower() for word in WORD_RE.findall(text) if word.lower() not in STOP_WORDS]


def summarize(text: str, sentence_count: int = 3) -> str:
    if sentence_count < 1 or sentence_count > 10:
        raise ValueError("sentence_count must be between 1 and 10")
    sentences = [sentence.strip() for sentence in SENTENCE_RE.split(text) if len(sentence.split()) >= 4]
    if len(sentences) <= sentence_count:
        return " ".join(sentences)
    frequencies = Counter(_words(text))
    if not frequencies:
        return " ".join(sentences[:sentence_count])
    maximum = max(frequencies.values())
    scores: list[tuple[float, int]] = []
    for index, sentence in enumerate(sentences):
        words = _words(sentence)
        if not words or len(words) > 60:
            continue
        keyword_score = sum(frequencies[word] / maximum for word in words) / math.sqrt(len(words))
        lead_bonus = max(0.0, 0.25 - index * 0.025)
        scores.append((keyword_score + lead_bonus, index))
    selected = sorted(index for _, index in sorted(scores, reverse=True)[:sentence_count])
    return " ".join(sentences[index] for index in selected)

