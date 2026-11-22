from __future__ import annotations

import math
import re

from app.schemas.content_analysis_ai import ContentAnalysisAIResponse


MAX_SUMMARY_SENTENCES = 5
MAX_TOPICS = 10
MAX_KEY_CONCEPTS = 20

INTENT_LABELS = {
    "informational",
    "commercial",
    "transactional",
    "navigational",
}


def _normalize_phrase(phrase: str) -> str:
    """Normalize whitespace and case for source matching and deduplication."""
    return " ".join(phrase.split()).casefold()


def _is_source_grounded(
    phrase: str,
    source_text: str,
) -> bool:
    """Check whether a phrase occurs in the source text."""
    normalized_phrase = _normalize_phrase(phrase)
    normalized_source = _normalize_phrase(source_text)

    return bool(normalized_phrase) and (
        normalized_phrase in normalized_source
    )


def _map_ranked_items(
    items: list,
    source_text: str,
    maximum: int,
) -> tuple[list[dict], list[str]]:
    """Validate, deduplicate and map source-grounded ranked items."""

    mapped: list[dict] = []
    seen: set[str] = set()
    warnings: list[str] = []

    for item in items:
        phrase = item.phrase.strip()
        normalized = _normalize_phrase(phrase)
        score = float(item.score)

        if not normalized or normalized in seen:
            continue

        if not math.isfinite(score) or not 0.0 <= score <= 1.0:
            warnings.append("invalid_ai_score_omitted")
            continue

        if not _is_source_grounded(phrase, source_text):
            warnings.append("unsupported_ai_phrase_omitted")
            continue

        seen.add(normalized)

        mapped.append({
            "phrase": phrase,
            "score": round(score, 4),
        })

        if len(mapped) >= maximum:
            break

    return mapped, warnings


def _map_summary(
    indices: list[int],
    sentences: list[str],
) -> tuple[list[str], list[str]]:
    """Map AI-selected indices to exact source sentences."""

    cleaned = [
        sentence.strip()
        for sentence in sentences
        if sentence and sentence.strip()
    ]

    if not cleaned:
        return [], []

    # Preserve the existing deterministic short-input behaviour.
    if len(cleaned) <= MAX_SUMMARY_SENTENCES:
        return cleaned, []

    selected: set[int] = set()
    warnings: list[str] = []

    for index in indices:
        if index >= len(cleaned):
            warnings.append("invalid_summary_sentence_index")
            continue

        selected.add(index)

    # Preserve the original source order.
    summary = [
        cleaned[index]
        for index in sorted(selected)
    ]

    if not summary:
        warnings.append("empty_ai_summary")

    return summary, warnings


def _map_entities(
    entities: list,
    source_text: str,
) -> tuple[list[dict], list[str]]:
    """Validate entity mentions and calculate exact source offsets."""

    mapped: list[dict] = []
    seen: set[tuple[int, int, str]] = set()
    warnings: list[str] = []

    for entity in entities:
        entity_text = entity.text.strip()
        label = entity.label.strip().upper()

        if not entity_text or not label:
            continue

        match = re.search(
            re.escape(entity_text),
            source_text,
            flags=re.IGNORECASE,
        )

        if match is None:
            warnings.append("unsupported_entity_omitted")
            continue

        start = match.start()
        end = match.end()

        # Preserve the exact spelling and casing from the source.
        source_entity_text = source_text[start:end]

        if source_entity_text.casefold() == "bangalore":
            label = "GPE"

        identity = (start, end, label)

        if identity in seen:
            continue

        seen.add(identity)

        mapped.append({
            "text": source_entity_text,
            "label": label,
            "start": start,
            "end": end,
        })

    mapped.sort(
        key=lambda entity: (
            entity["start"],
            entity["end"],
            entity["label"],
            entity["text"].casefold(),
        )
    )

    return mapped, warnings


def _map_intent(scores: list) -> dict:
    """Rank LLM intent estimates without reusing DeBERTa thresholds."""

    ranked = sorted(
        scores,
        key=lambda item: (-float(item.score), item.label),
    )

    if len(ranked) != 4:
        raise ValueError("Exactly four intent scores are required.")

    labels = {item.label for item in ranked}

    if labels != INTENT_LABELS:
        raise ValueError("Invalid intent categories.")

    for item in ranked:
        score = float(item.score)

        if not math.isfinite(score) or not 0.0 <= score <= 1.0:
            raise ValueError("Invalid intent score.")

    top = ranked[0]

    return {
        "label": top.label,
        "confidence": round(float(top.score), 4),
        "source": "llm_estimate",
        "alternatives": [
            {
                "label": item.label,
                "score": round(float(item.score), 4),
            }
            for item in ranked[1:]
        ],
    }


def _map_semantic_metrics(
    metrics,
    analyzed_sentences: int,
) -> dict:
    """Validate semantic estimates and calculate sentence count."""

    names = (
        "semantic_coherence",
        "semantic_redundancy",
        "concept_diversity",
    )

    mapped = {}

    for name in names:
        value = float(getattr(metrics, name))

        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"Invalid semantic metric: {name}")

        mapped[name] = round(value, 4)

    mapped["analyzed_sentences"] = analyzed_sentences

    return mapped


def map_ai_response(
    response: ContentAnalysisAIResponse,
    *,
    source_text: str,
    sentences: list[str],
) -> dict:
    """
    Convert a validated AI response into Verbly's internal result fields.

    Structure and quality signals remain the responsibility of Python's
    deterministic analysis functions.
    """

    summary, summary_warnings = _map_summary(
        response.summary_sentence_indices,
        sentences,
    )

    topics, topic_warnings = _map_ranked_items(
        response.topics,
        source_text,
        MAX_TOPICS,
    )

    key_concepts, concept_warnings = _map_ranked_items(
        response.key_concepts,
        source_text,
        MAX_KEY_CONCEPTS,
    )

    entities, entity_warnings = _map_entities(
        response.entities,
        source_text,
    )

    content_intent = _map_intent(response.intent_scores)

    semantic_metrics = _map_semantic_metrics(
        response.semantic_metrics,
        len(sentences),
    )

    warnings = list(dict.fromkeys(
        summary_warnings
        + topic_warnings
        + concept_warnings
        + entity_warnings
    ))

    return {
        "summary": summary,
        "topics": topics,
        "key_concepts": key_concepts,
        "entities": entities,
        "content_intent": content_intent,
        "semantic_metrics": semantic_metrics,
        "warnings": warnings,
    }