"""Deterministic keyword extraction from plain text (stdlib only)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.seo.constants import (
    MAX_TOKENS_ANALYZED,
    MIN_KEYWORD_LENGTH,
    STOPWORDS,
)

# Word = a run of unicode letters/digits/internal apostrophes (so "don't"
# stays one token). Punctuation and HTML entities (already decoded by the
# parser) are never counted as part of a token.
_WORD_RE = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?", re.UNICODE)


@dataclass(frozen=True)
class KeywordStat:
    keyword: str
    count: int
    density: float  # percentage of total (post-filter) tokens, rounded to 2dp


def tokenize(text: str) -> list[str]:
    """Lowercase, punctuation-stripped word tokens, in reading order."""
    return [match.group(0).lower() for match in _WORD_RE.finditer(text or "")]


def extract_keywords(text: str, *, max_keywords: int) -> list[KeywordStat]:
    """
    Extract the top ``max_keywords`` keywords from ``text``.

    Deterministic: identical input always yields identical output, in a
    stable order (count descending, then alphabetical for ties -- never
    insertion order or dict iteration order left to chance).

    Handles empty/short/stopword-only text safely by returning an empty
    list rather than raising or dividing by zero.
    """
    tokens = tokenize(text)[:MAX_TOKENS_ANALYZED]

    meaningful = [
        token
        for token in tokens
        if len(token) >= MIN_KEYWORD_LENGTH and token not in STOPWORDS
    ]

    total_meaningful = len(meaningful)
    if total_meaningful == 0:
        return []

    counts: dict[str, int] = {}
    for token in meaningful:
        counts[token] = counts.get(token, 0) + 1

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))

    return [
        KeywordStat(
            keyword=keyword,
            count=count,
            density=round((count / total_meaningful) * 100, 2),
        )
        for keyword, count in ranked[:max_keywords]
    ]
