from __future__ import annotations

from app.services.content_analysis.structure import analyze_structure


def test_structure_analysis() -> None:
    text = """Introduction

Artificial intelligence is changing many industries.

- Machine learning analyzes data.
- Natural language processing works with text.

Applications
AI systems can analyze large collections of documents efficiently.
"""

    sentences = [
        "Artificial intelligence is changing many industries.",
        "Machine learning analyzes data.",
        "Natural language processing works with text.",
        "AI systems can analyze large collections of documents efficiently.",
    ]

    result = analyze_structure(text, sentences)

    assert result.paragraph_count == 4
    assert result.sentence_count == 4
    assert result.average_words_per_sentence > 0
    assert result.shortest_sentence_words > 0
    assert result.longest_sentence_words >= result.shortest_sentence_words
    assert result.heading_like_count >= 2
    assert result.list_item_count == 2


def test_empty_structure() -> None:
    result = analyze_structure("", [])

    assert result.paragraph_count == 0
    assert result.sentence_count == 0
    assert result.average_words_per_sentence == 0.0
    assert result.shortest_sentence_words == 0
    assert result.longest_sentence_words == 0
    assert result.heading_like_count == 0
    assert result.list_item_count == 0


def test_sentence_length_distribution() -> None:
    text = (
        "Short sentence. "
        "This is a medium length sentence containing several words."
    )

    sentences = [
        "Short sentence.",
        "This is a medium length sentence containing several words.",
    ]

    result = analyze_structure(text, sentences)

    assert result.short_sentence_count == 1
    assert result.long_sentence_count == 0