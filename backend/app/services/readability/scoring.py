"""
Flesch Reading Ease / Flesch-Kincaid Grade Level formulas, plus the
human-readable interpretation of a Flesch Reading Ease score.

Kept separate from ``text_stats.py`` (raw counting primitives) and
``service.py`` (orchestration) so each module has one responsibility.
"""
from __future__ import annotations

#: Standard Flesch Reading Ease interpretation bands, checked from the
#: top down. The bounds below 0 and above 100 are open-ended: real text
#: can score outside 0-100, and it should still resolve to the nearest
#: end of the scale rather than falling through unclassified.
_READING_LEVEL_BANDS: tuple[tuple[float, str], ...] = (
    (90.0, "Very Easy"),
    (80.0, "Easy"),
    (70.0, "Fairly Easy"),
    (60.0, "Standard"),
    (50.0, "Fairly Difficult"),
    (30.0, "Difficult"),
)
_VERY_DIFFICULT = "Very Difficult"
UNDETERMINED = "Undetermined"


def flesch_reading_ease(average_words_per_sentence: float, average_syllables_per_word: float) -> float:
    """Standard Flesch Reading Ease formula."""
    return (
        206.835
        - 1.015 * average_words_per_sentence
        - 84.6 * average_syllables_per_word
    )


def flesch_kincaid_grade(average_words_per_sentence: float, average_syllables_per_word: float) -> float:
    """Standard Flesch-Kincaid Grade Level formula."""
    return (
        0.39 * average_words_per_sentence
        + 11.8 * average_syllables_per_word
        - 15.59
    )


def interpret_reading_ease(score: float) -> str:
    """
    Map a Flesch Reading Ease score to its standard human-readable
    interpretation label (e.g. "Standard", "Very Easy").
    """
    for threshold, label in _READING_LEVEL_BANDS:
        if score >= threshold:
            return label
    return _VERY_DIFFICULT
