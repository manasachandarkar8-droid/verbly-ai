from __future__ import annotations

from dataclasses import dataclass

from app.services.content_analysis.model_manager import ModelManager


INTENT_LABELS = (
    "informational",
    "commercial",
    "transactional",
    "navigational",
)

LOW_MARGIN_THRESHOLD = 0.10
MIXED_MARGIN_THRESHOLD = 0.08


@dataclass(frozen=True)
class IntentAlternative:
    label: str
    score: float


@dataclass(frozen=True)
class IntentResult:
    label: str
    confidence: float
    source: str
    alternatives: tuple[IntentAlternative, ...]


def _build_intent_text(
    title: str | None,
    description: str | None,
    leading_sentences: list[str],
) -> str:
    parts: list[str] = []

    if title:
        parts.append(f"Title: {title.strip()}")

    if description:
        parts.append(f"Description: {description.strip()}")

    for sentence in leading_sentences[:5]:
        cleaned = sentence.strip()

        if cleaned:
            parts.append(cleaned)

    return "\n".join(parts).strip()


def _normalize_label(label: str) -> str:
    return label.strip().casefold()


def _apply_mixed_other_rule(
    ranked: list[tuple[str, float]],
) -> tuple[str, str]:
    """
    Apply the deterministic mixed/other rule over the four real model labels.

    mixed/other is never passed to the zero-shot model.
    """

    if not ranked:
        return "mixed/other", "low_margin_rule"

    top_label, top_score = ranked[0]

    if len(ranked) == 1:
        return top_label, "model"

    second_score = ranked[1][1]
    margin = top_score - second_score

    if top_score < LOW_MARGIN_THRESHOLD:
        return "mixed/other", "low_margin_rule"

    if margin < MIXED_MARGIN_THRESHOLD:
        return "mixed/other", "low_margin_rule"

    return top_label, "model"


def classify_intent(
    title: str | None,
    description: str | None,
    leading_sentences: list[str],
    model_manager: ModelManager,
) -> IntentResult:
    """
    Classify content intent using one bounded DeBERTa inference.

    The model receives title, description, and a small number of leading
    analyzed sentences. It is never run once per semantic chunk.
    """

    text = _build_intent_text(
        title=title,
        description=description,
        leading_sentences=leading_sentences,
    )

    if not text:
        return IntentResult(
            label="mixed/other",
            confidence=0.0,
            source="low_margin_rule",
            alternatives=(),
        )

    classifier = model_manager.intent_classifier

    result = classifier(
        text,
        candidate_labels=list(INTENT_LABELS),
        multi_label=False,
        truncation=True,
    )

    raw_labels = result.get("labels", [])
    raw_scores = result.get("scores", [])

    ranked = sorted(
        (
            (
                _normalize_label(label),
                float(score),
            )
            for label, score in zip(raw_labels, raw_scores)
            if _normalize_label(label) in INTENT_LABELS
        ),
        key=lambda item: (-item[1], item[0]),
    )

    if not ranked:
        return IntentResult(
            label="mixed/other",
            confidence=0.0,
            source="low_margin_rule",
            alternatives=(),
        )

    final_label, source = _apply_mixed_other_rule(ranked)

    alternatives = tuple(
        IntentAlternative(
            label=label,
            score=round(score, 4),
        )
        for label, score in ranked[1:4]
    )

    confidence = round(ranked[0][1], 4)

    return IntentResult(
        label=final_label,
        confidence=confidence,
        source=source,
        alternatives=alternatives,
    )