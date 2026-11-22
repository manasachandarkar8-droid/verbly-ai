from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.services.content_analysis.embeddings import (
    generate_embeddings,
)
from app.services.content_analysis.model_manager import ModelManager
from app.services.content_analysis.preprocessing import build_semantic_chunks


REDUNDANCY_THRESHOLD = 0.88
MAX_SEMANTIC_SENTENCES = 400


@dataclass(frozen=True)
class SemanticMetricsResult:
    semantic_coherence: float
    semantic_redundancy: float
    concept_diversity: float
    analyzed_sentences: int


def _pairwise_similarities(embeddings: np.ndarray) -> np.ndarray:
    """Calculate pairwise similarities for normalized embeddings."""
    if len(embeddings) == 0:
        return np.empty((0, 0), dtype=np.float32)

    return embeddings @ embeddings.T


def _average_adjacent_similarity(similarities: np.ndarray) -> float:
    """Measure semantic similarity between consecutive items."""
    count = similarities.shape[0]

    if count < 2:
        return 1.0

    values = [
        float(similarities[index, index + 1])
        for index in range(count - 1)
    ]

    return float(np.mean(values))


def _redundancy_score(similarities: np.ndarray) -> float:
    """Measure the proportion of pairs above the redundancy threshold."""
    count = similarities.shape[0]

    if count < 2:
        return 0.0

    upper = similarities[np.triu_indices(count, k=1)]

    if upper.size == 0:
        return 0.0

    return float(np.mean(upper >= REDUNDANCY_THRESHOLD))


def _concept_diversity(similarities: np.ndarray) -> float:
    """Estimate semantic diversity from average pairwise similarity."""
    count = similarities.shape[0]

    if count < 2:
        return 0.0

    upper = similarities[np.triu_indices(count, k=1)]

    if upper.size == 0:
        return 0.0

    average_similarity = float(np.mean(upper))
    return 1.0 - max(0.0, min(1.0, average_similarity))


def analyze_semantic_metrics(
    sentences: list[str],
    model_manager: ModelManager,
) -> SemanticMetricsResult:
    """
    Calculate bounded semantic metrics using the shared MiniLM model.

    The input sentence count is capped before embeddings are generated.
    Embeddings are generated for bounded semantic chunks rather than
    independently embedding every sentence.
    """
    bounded_sentences = [
        sentence.strip()
        for sentence in sentences[:MAX_SEMANTIC_SENTENCES]
        if sentence and sentence.strip()
    ]

    count = len(bounded_sentences)

    if count == 0:
        return SemanticMetricsResult(
            semantic_coherence=0.0,
            semantic_redundancy=0.0,
            concept_diversity=0.0,
            analyzed_sentences=0,
        )

    if count == 1:
        return SemanticMetricsResult(
            semantic_coherence=1.0,
            semantic_redundancy=0.0,
            concept_diversity=0.0,
            analyzed_sentences=1,
        )

    chunks, _ = build_semantic_chunks(tuple(bounded_sentences))

    if len(chunks) < 2:
        return SemanticMetricsResult(
            semantic_coherence=1.0,
            semantic_redundancy=0.0,
            concept_diversity=0.0,
            analyzed_sentences=count,
        )

    embedding_result = generate_embeddings(
        list(chunks),
        model_manager,
    )

    embeddings = np.asarray(
        embedding_result.embeddings,
        dtype=np.float32,
    )

    if embeddings.ndim != 2 or embeddings.shape[0] < 2:
        return SemanticMetricsResult(
            semantic_coherence=0.0,
            semantic_redundancy=0.0,
            concept_diversity=0.0,
            analyzed_sentences=count,
        )

    similarities = _pairwise_similarities(embeddings)

    coherence = _average_adjacent_similarity(similarities)
    redundancy = _redundancy_score(similarities)
    diversity = _concept_diversity(similarities)

    return SemanticMetricsResult(
        semantic_coherence=round(
            max(0.0, min(1.0, coherence)),
            4,
        ),
        semantic_redundancy=round(
            max(0.0, min(1.0, redundancy)),
            4,
        ),
        concept_diversity=round(
            max(0.0, min(1.0, diversity)),
            4,
        ),
        analyzed_sentences=count,
    )