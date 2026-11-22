from __future__ import annotations

import numpy as np

from app.services.content_analysis.embeddings import (
    cosine_similarity,
    generate_embeddings,
)
from app.services.content_analysis.model_manager import ModelManager


def test_generate_embeddings() -> None:
    manager = ModelManager()

    result = generate_embeddings(
        [
            "Artificial intelligence analyzes website content.",
            "Machine learning can understand textual information.",
        ],
        manager,
    )

    assert result.embeddings.shape[0] == 2
    assert result.embeddings.shape[1] > 0
    assert result.dimensions == result.embeddings.shape[1]


def test_embeddings_are_normalized() -> None:
    manager = ModelManager()

    result = generate_embeddings(
        ["Artificial intelligence is useful."],
        manager,
    )

    norm = np.linalg.norm(result.embeddings[0])

    assert np.isclose(norm, 1.0, atol=1e-5)


def test_empty_input_returns_empty_embeddings() -> None:
    manager = ModelManager()

    result = generate_embeddings([], manager)

    assert result.embeddings.shape == (0, 0)
    assert result.dimensions == 0


def test_cosine_similarity_identical_vectors() -> None:
    vector = np.array([1.0, 0.0, 0.0], dtype=np.float32)

    similarity = cosine_similarity(vector, vector)

    assert np.isclose(similarity, 1.0)


def test_cosine_similarity_orthogonal_vectors() -> None:
    first = np.array([1.0, 0.0], dtype=np.float32)
    second = np.array([0.0, 1.0], dtype=np.float32)

    similarity = cosine_similarity(first, second)

    assert np.isclose(similarity, 0.0)


def test_cosine_similarity_rejects_dimension_mismatch() -> None:
    first = np.array([1.0, 0.0], dtype=np.float32)
    second = np.array([1.0, 0.0, 0.0], dtype=np.float32)

    try:
        cosine_similarity(first, second)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for dimension mismatch")