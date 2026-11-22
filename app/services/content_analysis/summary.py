from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.services.content_analysis.embeddings import cosine_similarity
from app.services.content_analysis.model_manager import ModelManager


MAX_SUMMARY_SENTENCES = 5
REDUNDANCY_THRESHOLD = 0.88


@dataclass(frozen=True)
class SummaryResult:
    sentences: tuple[str, ...]


def _centrality_scores(embeddings: np.ndarray) -> np.ndarray:
    if embeddings.shape[0] == 0:
        return np.empty(0, dtype=np.float32)

    if embeddings.shape[0] == 1:
        return np.ones(1, dtype=np.float32)

    similarity_matrix = np.matmul(
        embeddings,
        embeddings.T,
    )

    np.fill_diagonal(similarity_matrix, 0.0)

    return similarity_matrix.mean(axis=1)


def _position_scores(sentence_count: int) -> np.ndarray:
    if sentence_count == 0:
        return np.empty(0, dtype=np.float32)

    if sentence_count == 1:
        return np.ones(1, dtype=np.float32)

    positions = np.arange(sentence_count, dtype=np.float32)

    return 1.0 - (positions / sentence_count) * 0.25


def _importance_scores(
    embeddings: np.ndarray,
) -> np.ndarray:
    centrality = _centrality_scores(embeddings)

    if centrality.size == 0:
        return centrality

    min_value = float(centrality.min())
    max_value = float(centrality.max())

    if max_value == min_value:
        return np.ones_like(centrality)

    return (centrality - min_value) / (max_value - min_value)


def summarize(
    sentences: list[str],
    model_manager: ModelManager,
) -> SummaryResult:
    """
    Generate a deterministic extractive summary.

    Only sentences already present in the source text can appear in the
    returned summary.
    """

    cleaned = [
        sentence.strip()
        for sentence in sentences
        if sentence and sentence.strip()
    ]

    if not cleaned:
        return SummaryResult(sentences=())

    if len(cleaned) <= MAX_SUMMARY_SENTENCES:
        return SummaryResult(sentences=tuple(cleaned))

    embedding_result = model_manager.embeddings.encode(
        cleaned,
        batch_size=16,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    embeddings = np.asarray(
        embedding_result,
        dtype=np.float32,
    )

    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)

    importance = _importance_scores(embeddings)
    position = _position_scores(len(cleaned))

    combined_scores = (
        0.75 * importance
        + 0.25 * position
    )

    ranked_indices = sorted(
        range(len(cleaned)),
        key=lambda index: (
            -float(combined_scores[index]),
            index,
        ),
    )

    selected: list[int] = []

    for index in ranked_indices:
        if len(selected) >= MAX_SUMMARY_SENTENCES:
            break

        is_redundant = any(
            cosine_similarity(
                embeddings[index],
                embeddings[other_index],
            )
            >= REDUNDANCY_THRESHOLD
            for other_index in selected
        )

        if is_redundant:
            continue

        selected.append(index)

    # If redundancy suppression removed too many candidates, fill remaining
    # slots with the highest-ranked unused sentences.
    if len(selected) < MAX_SUMMARY_SENTENCES:
        for index in ranked_indices:
            if index not in selected:
                selected.append(index)

            if len(selected) >= MAX_SUMMARY_SENTENCES:
                break

    selected.sort()

    return SummaryResult(
        sentences=tuple(
            cleaned[index]
            for index in selected
        )
    )