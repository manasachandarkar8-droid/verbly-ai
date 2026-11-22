"""Feature 2 orchestration: raw text -> structured readability result."""
from __future__ import annotations

from dataclasses import dataclass

from app.services.readability.scoring import (
    UNDETERMINED,
    flesch_kincaid_grade,
    flesch_reading_ease,
    interpret_reading_ease,
)
from app.services.readability.text_stats import (
    count_sentences,
    extract_words,
    normalize_whitespace,
    total_syllables,
)

#: Number of decimal places used when rounding computed metrics. Rounding
#: happens once, here, at the orchestration boundary -- the underlying
#: formulas and counts stay full-precision.
_ROUND_DIGITS = 2


@dataclass(frozen=True)
class ReadabilityResult:
    word_count: int
    sentence_count: int
    character_count: int
    average_words_per_sentence: float
    average_syllables_per_word: float
    flesch_reading_ease: float
    flesch_kincaid_grade: float
    reading_level: str


def analyze_readability(text: str) -> ReadabilityResult:
    """
    Compute deterministic readability metrics for ``text``.

    Handles empty/whitespace-only input gracefully (no exceptions, no
    division by zero): such input yields all-zero counts and a
    "Undetermined" reading level rather than a crash or a misleading
    score.
    """
    raw = text or ""
    character_count = len(raw.strip())

    normalized = normalize_whitespace(raw)
    words = extract_words(normalized)
    word_count = len(words)

    if word_count == 0:
        return ReadabilityResult(
            word_count=0,
            sentence_count=0,
            character_count=character_count,
            average_words_per_sentence=0.0,
            average_syllables_per_word=0.0,
            flesch_reading_ease=0.0,
            flesch_kincaid_grade=0.0,
            reading_level=UNDETERMINED,
        )

    sentence_count = count_sentences(normalized)
    syllable_count = total_syllables(words)

    average_words_per_sentence = word_count / sentence_count
    average_syllables_per_word = syllable_count / word_count

    reading_ease = flesch_reading_ease(average_words_per_sentence, average_syllables_per_word)
    grade_level = flesch_kincaid_grade(average_words_per_sentence, average_syllables_per_word)

    return ReadabilityResult(
        word_count=word_count,
        sentence_count=sentence_count,
        character_count=character_count,
        average_words_per_sentence=round(average_words_per_sentence, _ROUND_DIGITS),
        average_syllables_per_word=round(average_syllables_per_word, _ROUND_DIGITS),
        flesch_reading_ease=round(reading_ease, _ROUND_DIGITS),
        flesch_kincaid_grade=round(grade_level, _ROUND_DIGITS),
        reading_level=interpret_reading_ease(reading_ease),
    )
