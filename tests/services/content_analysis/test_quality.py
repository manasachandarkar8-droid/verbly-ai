from __future__ import annotations

from app.services.content_analysis.quality import analyze_quality


def test_quality_signals_for_normal_content() -> None:
    text = (
        "Artificial intelligence helps organizations analyze information. "
        "Machine learning systems can identify useful patterns in documents. "
        "Natural language processing allows applications to understand text."
    )

    result = analyze_quality(
        text=text,
        sentence_count=3,
        average_words_per_sentence=12.0,
    )

    assert result.word_count > 0
    assert result.unique_word_count > 0
    assert 0.0 <= result.vocabulary_diversity <= 1.0
    assert 0.0 <= result.repeated_word_ratio <= 1.0
    assert result.short_content is False
    assert result.english_likelihood > 0.5


def test_short_content_signal() -> None:
    result = analyze_quality(
        text="AI analyzes text.",
        sentence_count=1,
        average_words_per_sentence=3.0,
    )

    assert result.short_content is True
    assert "content_too_short" in result.warnings


def test_repetitive_content_signal() -> None:
    text = "test " * 100

    result = analyze_quality(
        text=text,
        sentence_count=1,
        average_words_per_sentence=100.0,
    )

    assert result.repetitive_content is True
    assert "high_repetition" in result.warnings


def test_empty_content() -> None:
    result = analyze_quality(
        text="",
        sentence_count=0,
        average_words_per_sentence=0.0,
    )

    assert result.word_count == 0
    assert result.unique_word_count == 0
    assert result.vocabulary_diversity == 0.0
    assert result.repeated_word_ratio == 0.0
    assert result.short_content is True
    assert result.english_likelihood == 0.0


def test_non_english_likelihood_is_descriptive() -> None:
    text = "你好 世界 こんにちは"

    result = analyze_quality(
        text=text,
        sentence_count=1,
        average_words_per_sentence=3.0,
    )

    assert 0.0 <= result.english_likelihood <= 1.0
    assert "low_english_likelihood" in result.warnings