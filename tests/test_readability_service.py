from __future__ import annotations

import pytest

from app.services.readability.service import ReadabilityResult, analyze_readability


# --- graceful handling of degenerate input ---------------------------------


def test_empty_text_does_not_crash_and_is_zeroed():
    result = analyze_readability("")
    assert result == ReadabilityResult(
        word_count=0,
        sentence_count=0,
        character_count=0,
        average_words_per_sentence=0.0,
        average_syllables_per_word=0.0,
        flesch_reading_ease=0.0,
        flesch_kincaid_grade=0.0,
        reading_level="Undetermined",
    )


def test_whitespace_only_text_does_not_crash_and_is_zeroed():
    result = analyze_readability("     \n\t   ")
    assert result.word_count == 0
    assert result.sentence_count == 0
    assert result.reading_level == "Undetermined"
    assert result.average_words_per_sentence == 0.0
    assert result.average_syllables_per_word == 0.0


def test_punctuation_only_text_does_not_crash():
    result = analyze_readability("... !! ??")
    assert result.word_count == 0
    assert result.reading_level == "Undetermined"


# --- small, real inputs (division-by-zero guards) --------------------------


def test_one_word_text_is_safe():
    result = analyze_readability("Hello")
    assert result.word_count == 1
    assert result.sentence_count == 1
    assert result.average_words_per_sentence == 1.0
    assert result.average_syllables_per_word == pytest.approx(2.0)  # "hel-lo"


def test_one_sentence_text():
    result = analyze_readability("This is a short sentence.")
    assert result.word_count == 5
    assert result.sentence_count == 1
    assert result.average_words_per_sentence == 5.0


def test_multiple_sentences_counted_correctly():
    text = "Hello world. This is great! Are you sure? Yes."
    result = analyze_readability(text)
    assert result.sentence_count == 4
    assert result.word_count == 9


# --- normal paragraphs / punctuation / abbreviations ------------------------


def test_normal_paragraph_produces_sane_metrics():
    text = (
        "The quick brown fox jumps over the lazy dog. "
        "It was a bright, cold morning in the forest. "
        "Birds sang softly as the sun rose over the hills."
    )
    result = analyze_readability(text)
    assert result.word_count > 0
    assert result.sentence_count == 3
    assert result.average_words_per_sentence > 0
    assert result.average_syllables_per_word > 0
    assert isinstance(result.flesch_reading_ease, float)
    assert isinstance(result.flesch_kincaid_grade, float)
    assert result.reading_level != "Undetermined"


def test_abbreviations_do_not_inflate_sentence_count():
    text = "Dr. Smith arrived early. Mrs. Lee greeted him warmly."
    result = analyze_readability(text)
    assert result.sentence_count == 2


def test_unusual_punctuation_does_not_crash():
    text = "Wait... what?! Is this real?!?! Yes -- totally."
    result = analyze_readability(text)
    assert result.word_count > 0
    assert result.sentence_count >= 1


# --- known worked example (hand-verified against the exact formulas) -------


def test_known_readability_example_matches_hand_calculation():
    # "The cat sat on the mat." -> 6 words, 1 sentence, 6 syllables
    # (every word here is exactly one syllable under our heuristic).
    text = "The cat sat on the mat."
    result = analyze_readability(text)

    assert result.word_count == 6
    assert result.sentence_count == 1
    assert result.average_words_per_sentence == 6.0
    assert result.average_syllables_per_word == 1.0

    # 206.835 - 1.015*6 - 84.6*1.0 = 116.145 -> rounds to 116.15
    assert result.flesch_reading_ease == 116.15
    # 0.39*6 + 11.8*1.0 - 15.59 = -1.45
    assert result.flesch_kincaid_grade == -1.45
    assert result.reading_level == "Very Easy"


# --- determinism -----------------------------------------------------------


def test_repeated_calls_are_deterministic():
    text = "Repeated analysis of the same text must always produce the same result."
    first = analyze_readability(text)
    second = analyze_readability(text)
    third = analyze_readability(text)
    assert first == second == third
