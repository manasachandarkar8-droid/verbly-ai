from __future__ import annotations

from app.services.content_analysis.model_manager import ModelManager
from app.services.content_analysis.summary import (
    MAX_SUMMARY_SENTENCES,
    summarize,
)


def test_summary_returns_source_sentences() -> None:
    manager = ModelManager()

    sentences = [
        "Artificial intelligence is transforming many industries.",
        "Machine learning is one important branch of artificial intelligence.",
        "Website analysis can use artificial intelligence to understand content.",
        "Semantic embeddings help systems compare pieces of text.",
        "Named entity recognition identifies people and organizations.",
        "Natural language processing enables computers to work with language.",
    ]

    result = summarize(sentences, manager)

    assert result.sentences
    assert len(result.sentences) <= MAX_SUMMARY_SENTENCES

    for sentence in result.sentences:
        assert sentence in sentences


def test_short_input_is_returned_without_generation() -> None:
    manager = ModelManager()

    sentences = [
        "First sentence.",
        "Second sentence.",
    ]

    result = summarize(sentences, manager)

    assert result.sentences == tuple(sentences)


def test_empty_input_returns_empty_summary() -> None:
    manager = ModelManager()

    result = summarize([], manager)

    assert result.sentences == ()


def test_summary_has_no_duplicate_sentences() -> None:
    manager = ModelManager()

    sentences = [
        "Artificial intelligence is useful for content analysis.",
        "Artificial intelligence is useful for content analysis.",
        "Machine learning can analyze textual information.",
        "Semantic models compare textual meaning.",
        "Named entity recognition extracts entities.",
        "Content analysis helps improve websites.",
    ]

    result = summarize(sentences, manager)

    assert len(result.sentences) == len(set(result.sentences))