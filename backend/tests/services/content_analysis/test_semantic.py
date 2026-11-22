from __future__ import annotations

from unittest.mock import Mock, patch

import numpy as np

from app.services.content_analysis.embeddings import EmbeddingResult
from app.services.content_analysis.semantic import analyze_semantic_metrics


def test_empty_content_returns_safe_result() -> None:
    result = analyze_semantic_metrics(
        [],
        model_manager=Mock(),
    )

    assert result.semantic_coherence == 0.0
    assert result.semantic_redundancy == 0.0
    assert result.concept_diversity == 0.0
    assert result.analyzed_sentences == 0


def test_single_sentence_returns_safe_result() -> None:
    result = analyze_semantic_metrics(
        ["Artificial intelligence is useful."],
        model_manager=Mock(),
    )

    assert result.semantic_coherence == 1.0
    assert result.semantic_redundancy == 0.0
    assert result.concept_diversity == 0.0
    assert result.analyzed_sentences == 1


def test_semantically_similar_sentences_have_high_coherence() -> None:
    embeddings = np.array(
        [
            [1.0, 0.0],
            [0.99, 0.1],
            [0.98, 0.2],
        ],
        dtype=np.float32,
    )

    with patch(
        "app.services.content_analysis.semantic.generate_embeddings",
        return_value=EmbeddingResult(
            embeddings=embeddings.tolist(),
            dimensions=2,
        ),
    ):
        result = analyze_semantic_metrics(
            [
                "Artificial intelligence helps companies.",
                "AI helps organizations improve productivity.",
                "Machine learning helps businesses automate tasks.",
            ],
            model_manager=Mock(),
        )

    assert result.semantic_coherence > 0.9
    assert result.semantic_redundancy >= 0.0
    assert 0.0 <= result.concept_diversity <= 1.0


def test_different_sentences_have_lower_coherence() -> None:
    embeddings = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
            [-1.0, 0.0],
        ],
        dtype=np.float32,
    )

    with patch(
        "app.services.content_analysis.semantic.generate_embeddings",
        return_value=EmbeddingResult(
            embeddings=embeddings.tolist(),
            dimensions=2,
        ),
    ):
        result = analyze_semantic_metrics(
            [
                "Artificial intelligence is transforming healthcare.",
                "The restaurant serves traditional Indian food.",
                "The football match starts at seven.",
            ],
            model_manager=Mock(),
        )

    assert result.semantic_coherence < 0.5
    assert 0.0 <= result.semantic_redundancy <= 1.0
    assert 0.0 <= result.concept_diversity <= 1.0


def test_output_values_are_bounded() -> None:
    embeddings = np.array(
        [
            [1.0, 0.0],
            [0.9, 0.1],
        ],
        dtype=np.float32,
    )

    with patch(
        "app.services.content_analysis.semantic.generate_embeddings",
        return_value=EmbeddingResult(
            embeddings=embeddings.tolist(),
            dimensions=2,
        ),
    ):
        result = analyze_semantic_metrics(
            ["First sentence.", "Second sentence."],
            model_manager=Mock(),
        )

    assert 0.0 <= result.semantic_coherence <= 1.0
    assert 0.0 <= result.semantic_redundancy <= 1.0
    assert 0.0 <= result.concept_diversity <= 1.0

def test_semantic_analysis_respects_chunk_limit() -> None:
    sentences = [
        f"Sentence number {index} discusses a topic."
        for index in range(400)
    ]

    embeddings = np.tile(
        np.array([[1.0, 0.0]], dtype=np.float32),
        (20, 1),
    )

    with patch(
        "app.services.content_analysis.semantic.generate_embeddings",
        return_value=EmbeddingResult(
            embeddings=embeddings,
            dimensions=2,
        ),
    ) as mock_embeddings:
        result = analyze_semantic_metrics(
            sentences,
            model_manager=Mock(),
        )

    mock_embeddings.assert_called_once()

    analyzed_chunks = mock_embeddings.call_args.args[0]

    assert len(analyzed_chunks) <= 20
    assert result.analyzed_sentences == 400    