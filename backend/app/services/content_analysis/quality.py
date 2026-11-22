from __future__ import annotations

from dataclasses import dataclass
import re


_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

_MIN_USEFUL_WORDS = 20
_LOW_VOCABULARY_DIVERSITY = 0.35
_HIGH_REPETITION_RATIO = 0.25
_LOW_ENGLISH_LIKELIHOOD = 0.50


@dataclass(frozen=True)
class QualitySignalsResult:
    word_count: int
    unique_word_count: int
    vocabulary_diversity: float
    repeated_word_ratio: float
    average_words_per_sentence: float
    short_content: bool
    repetitive_content: bool
    english_likelihood: float
    warnings: tuple[str, ...]


def _extract_words(text: str) -> list[str]:
    return [match.group(0).lower() for match in _WORD_RE.finditer(text)]


def _english_likelihood(words: list[str]) -> float:
    if not words:
        return 0.0

    ascii_words = sum(word.isascii() for word in words)
    return round(ascii_words / len(words), 4)


def analyze_quality(
    text: str,
    sentence_count: int,
    average_words_per_sentence: float,
) -> QualitySignalsResult:
    words = _extract_words(text)

    word_count = len(words)
    unique_word_count = len(set(words))

    if word_count:
        vocabulary_diversity = unique_word_count / word_count
        repeated_word_ratio = 1.0 - vocabulary_diversity
    else:
        vocabulary_diversity = 0.0
        repeated_word_ratio = 0.0

    english_likelihood = _english_likelihood(words)

    short_content = word_count < _MIN_USEFUL_WORDS

    repetitive_content = (
        word_count > 0
        and (
            vocabulary_diversity < _LOW_VOCABULARY_DIVERSITY
            or repeated_word_ratio > _HIGH_REPETITION_RATIO
        )
    )

    warnings: list[str] = []

    if short_content:
        warnings.append("content_too_short")

    if repetitive_content:
        warnings.append("high_repetition")

    if sentence_count <= 0:
        warnings.append("sentence_detection_uncertain")

    if english_likelihood < _LOW_ENGLISH_LIKELIHOOD:
        warnings.append("low_english_likelihood")

    return QualitySignalsResult(
        word_count=word_count,
        unique_word_count=unique_word_count,
        vocabulary_diversity=round(vocabulary_diversity, 4),
        repeated_word_ratio=round(repeated_word_ratio, 4),
        average_words_per_sentence=round(average_words_per_sentence, 4),
        short_content=short_content,
        repetitive_content=repetitive_content,
        english_likelihood=english_likelihood,
        warnings=tuple(warnings),
    )