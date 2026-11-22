from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.services.content_analysis.model_manager import ModelManager


@dataclass(frozen=True)
class EmbeddingResult:
    embeddings: np.ndarray
    dimensions: int


def generate_embeddings(
    texts: list[str],
    model_manager: ModelManager,
) -> EmbeddingResult:
    """
    Generate normalized MiniLM embeddings for a bounded list of texts.

    The shared SentenceTransformer instance is obtained from ModelManager.
    """

    cleaned_texts = [
        text.strip()
        for text in texts
        if text and text.strip()
    ]

    if not cleaned_texts:
        return EmbeddingResult(
            embeddings=np.empty((0, 0), dtype=np.float32),
            dimensions=0,
        )

    embeddings = model_manager.embeddings.encode(
        cleaned_texts,
        batch_size=16,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32,
    )

    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)

    return EmbeddingResult(
        embeddings=embeddings,
        dimensions=int(embeddings.shape[1]),
    )


def cosine_similarity(
    first: np.ndarray,
    second: np.ndarray,
) -> float:
    """Calculate cosine similarity for two normalized or arbitrary vectors."""

    first_vector = np.asarray(first, dtype=np.float32).reshape(-1)
    second_vector = np.asarray(second, dtype=np.float32).reshape(-1)

    if first_vector.size == 0 or second_vector.size == 0:
        return 0.0

    if first_vector.shape != second_vector.shape:
        raise ValueError("Embedding dimensions must match.")

    first_norm = float(np.linalg.norm(first_vector))
    second_norm = float(np.linalg.norm(second_vector))

    if first_norm == 0.0 or second_norm == 0.0:
        return 0.0

    similarity = float(
        np.dot(first_vector, second_vector)
        / (first_norm * second_norm)
    )

    return max(-1.0, min(1.0, similarity))