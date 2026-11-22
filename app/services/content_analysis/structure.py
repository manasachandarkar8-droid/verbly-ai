from __future__ import annotations

from dataclasses import dataclass
import re


_WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)


@dataclass(frozen=True)
class StructureResult:
    paragraph_count: int
    sentence_count: int
    average_words_per_sentence: float
    shortest_sentence_words: int
    longest_sentence_words: int
    short_sentence_count: int
    long_sentence_count: int
    heading_like_count: int
    list_item_count: int


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _is_heading_like(line: str) -> bool:
    """
    Conservative heuristic for heading-like lines.

    A line is considered heading-like when it is short and visually
    resembles a standalone heading rather than a normal sentence.
    """

    stripped = line.strip()

    if not stripped:
        return False

    words = _word_count(stripped)

    if words == 0 or words > 12:
        return False

    if stripped.endswith((".", "!", "?")):
        return False

    return True


def _is_list_item(line: str) -> bool:
    stripped = line.strip()

    if not stripped:
        return False

    return bool(
        re.match(
            r"^(?:[-*•]|\d+[.)]|[A-Za-z][.)])\s+",
            stripped,
        )
    )


def analyze_structure(
    text: str,
    sentences: list[str],
) -> StructureResult:
    """Calculate deterministic structural characteristics of analyzed text."""

    if not text.strip():
        return StructureResult(
            paragraph_count=0,
            sentence_count=0,
            average_words_per_sentence=0.0,
            shortest_sentence_words=0,
            longest_sentence_words=0,
            short_sentence_count=0,
            long_sentence_count=0,
            heading_like_count=0,
            list_item_count=0,
        )

    paragraph_count = len(
        [
            paragraph
            for paragraph in re.split(r"\n\s*\n", text)
            if paragraph.strip()
        ]
    )

    sentence_word_counts = [
        _word_count(sentence)
        for sentence in sentences
        if sentence.strip()
    ]

    sentence_count = len(sentence_word_counts)

    if sentence_count:
        average_words = sum(sentence_word_counts) / sentence_count
        shortest = min(sentence_word_counts)
        longest = max(sentence_word_counts)

        short_count = sum(
            count < 8
            for count in sentence_word_counts
        )

        long_count = sum(
            count > 25
            for count in sentence_word_counts
        )
    else:
        average_words = 0.0
        shortest = 0
        longest = 0
        short_count = 0
        long_count = 0

    lines = text.splitlines()

    heading_like_count = sum(
        _is_heading_like(line)
        for line in lines
    )

    list_item_count = sum(
        _is_list_item(line)
        for line in lines
    )

    return StructureResult(
        paragraph_count=paragraph_count,
        sentence_count=sentence_count,
        average_words_per_sentence=round(average_words, 2),
        shortest_sentence_words=shortest,
        longest_sentence_words=longest,
        short_sentence_count=short_count,
        long_sentence_count=long_count,
        heading_like_count=heading_like_count,
        list_item_count=list_item_count,
    )