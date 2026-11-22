from __future__ import annotations

import pytest

from app.services.content_analysis.preprocessing import (
    MAX_ANALYSIS_CHARACTERS,
    MAX_ANALYZED_SENTENCES,
    MAX_REQUEST_CHARACTERS,
    MAX_SEMANTIC_CHUNKS,
    build_semantic_chunks,
    normalize_text,
    preprocess_text,
)


def test_unicode_normalization() -> None:
    text = "Cafe\u0301"

    result = normalize_text(text)

    assert result == "Café"


def test_zero_width_characters_are_removed() -> None:
    text = "hello\u200b world\uFEFF"

    result = normalize_text(text)

    assert result == "hello world"


def test_character_semantics() -> None:
    text = "Hello world. This is a test."

    result = preprocess_text(text)

    assert result.received_characters == len(text)
    assert result.original_characters == len("Hello world. This is a test.")
    assert result.analyzed_characters == len(result.text)


def test_empty_text_returns_valid_result() -> None:
    result = preprocess_text("   ")

    assert result.received_characters == 3
    assert result.original_characters == 0
    assert result.analyzed_characters == 0
    assert result.sentences == ()
    assert result.truncated is False
    assert result.truncation_reason is None


def test_request_limit_is_enforced() -> None:
    text = "a" * (MAX_REQUEST_CHARACTERS + 1)

    with pytest.raises(ValueError):
        preprocess_text(text)


def test_analysis_window_is_enforced() -> None:
    text = "Sentence one. " * 10_000

    result = preprocess_text(text)

    assert result.original_characters > MAX_ANALYSIS_CHARACTERS
    assert result.analyzed_characters <= MAX_ANALYSIS_CHARACTERS
    assert result.truncated is True
    assert result.truncation_reason == "characters"


def test_sentence_limit_is_enforced() -> None:
    text = "Sentence. " * (MAX_ANALYZED_SENTENCES + 50)

    result = preprocess_text(text)

    assert len(result.sentences) <= MAX_ANALYZED_SENTENCES
    assert result.truncated is True
    assert result.truncation_reason == "sentences"


def test_semantic_chunk_limit_is_enforced() -> None:
    sentences = tuple(
        f"Sentence number {index}."
        for index in range(MAX_SEMANTIC_CHUNKS + 10)
    )

    chunks, truncated = build_semantic_chunks(sentences)

    assert len(chunks) <= MAX_SEMANTIC_CHUNKS
    assert truncated is True


def test_short_text_is_not_truncated() -> None:
    text = "Verbly analyzes website content."

    result = preprocess_text(text)

    assert result.truncated is False
    assert result.truncation_reason is None
    assert result.text == text


def test_sentence_boundaries_are_preserved() -> None:
    text = "First sentence. Second sentence! Third sentence?"

    result = preprocess_text(text)

    assert len(result.sentences) == 3
    assert result.sentences[0] == "First sentence."
    assert result.sentences[1] == "Second sentence!"
    assert result.sentences[2] == "Third sentence?"



def test_paragraph_boundaries_are_preserved() -> None:
    text = (
        "First paragraph sentence one. "
        "First paragraph sentence two.\n\n"
        "Second paragraph sentence."
    )

    result = preprocess_text(text)

    assert "\n\n" in result.text
    assert result.text == text
    assert result.sentences == (
        "First paragraph sentence one.",
        "First paragraph sentence two.",
        "Second paragraph sentence.",
    )


def test_zero_width_joiner_is_preserved() -> None:
    text = "Technologist: 👩\u200d💻"

    assert normalize_text(text) == text


def test_control_characters_and_lone_surrogates_are_removed() -> None:
    text = "a\x00b\x07c\ud800d"

    assert normalize_text(text) == "abcd"


def test_quoted_sentence_boundaries_are_preserved() -> None:
    text = '"First sentence." "Second sentence!"'

    result = preprocess_text(text)

    assert result.sentences == (
        '"First sentence."',
        '"Second sentence!"',
    )


def test_common_abbreviation_does_not_split_sentence() -> None:
    text = "Dr. Smith studies artificial intelligence. Next sentence."

    result = preprocess_text(text)

    assert result.sentences == (
        "Dr. Smith studies artificial intelligence.",
        "Next sentence.",
    )


def test_character_truncation_preserves_complete_sentence_when_possible() -> None:
    text = "A complete sentence. " * 3_000

    result = preprocess_text(text)

    assert result.truncated is True
    assert result.truncation_reason == "characters"
    assert result.analyzed_characters <= MAX_ANALYSIS_CHARACTERS
    assert result.analyzed_characters == len(result.text)
    assert result.text.endswith(".")
    assert result.sentences[-1].endswith(".")


def test_sentence_limit_preserves_retained_text_and_paragraphs() -> None:
    paragraphs = [
        f"Paragraph {index} contains a complete sentence."
        for index in range(MAX_ANALYZED_SENTENCES + 10)
    ]
    text = "\n\n".join(paragraphs)

    result = preprocess_text(text)

    assert len(result.sentences) == MAX_ANALYZED_SENTENCES
    assert result.truncated is True
    assert result.truncation_reason == "sentences"
    assert result.text.endswith("complete sentence.")
    assert result.analyzed_characters == len(result.text)
    assert result.text.count("\n\n") == MAX_ANALYZED_SENTENCES - 1


def test_semantic_chunking_aggregates_without_losing_sentences() -> None:
    sentences = tuple(
        f"Unique sentence marker {index}."
        for index in range(MAX_SEMANTIC_CHUNKS + 10)
    )

    chunks, aggregated = build_semantic_chunks(sentences)

    assert len(chunks) == MAX_SEMANTIC_CHUNKS
    assert aggregated is True

    combined = " ".join(chunks)

    for sentence in sentences:
        assert sentence in combined