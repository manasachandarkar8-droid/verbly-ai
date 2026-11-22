from __future__ import annotations

from app.services.content_analysis.intent import (
    INTENT_LABELS,
    _apply_mixed_other_rule,
    classify_intent,
)
from app.services.content_analysis.model_manager import ModelManager


def test_intent_labels_are_fixed() -> None:
    assert INTENT_LABELS == (
        "informational",
        "commercial",
        "transactional",
        "navigational",
    )


def test_mixed_other_rule_accepts_clear_result() -> None:
    label, source = _apply_mixed_other_rule(
        [
            ("informational", 0.80),
            ("commercial", 0.10),
            ("transactional", 0.06),
            ("navigational", 0.04),
        ]
    )

    assert label == "informational"
    assert source == "model"


def test_mixed_other_rule_handles_low_margin() -> None:
    label, source = _apply_mixed_other_rule(
        [
            ("informational", 0.41),
            ("commercial", 0.38),
            ("transactional", 0.12),
            ("navigational", 0.09),
        ]
    )

    assert label == "mixed/other"
    assert source == "low_margin_rule"


def test_classify_intent() -> None:
    manager = ModelManager()

    result = classify_intent(
        title="Complete Guide to Artificial Intelligence",
        description="Learn how artificial intelligence works and why it matters.",
        leading_sentences=[
            "Artificial intelligence is a field of computer science.",
            "It enables machines to perform tasks that normally require human intelligence.",
        ],
        model_manager=manager,
    )

    assert result.label in (*INTENT_LABELS, "mixed/other")
    assert 0.0 <= result.confidence <= 1.0
    assert result.source in ("model", "low_margin_rule")
    assert len(result.alternatives) <= 3


def test_empty_intent_input_returns_mixed_other() -> None:
    manager = ModelManager()

    result = classify_intent(
        title=None,
        description=None,
        leading_sentences=[],
        model_manager=manager,
    )

    assert result.label == "mixed/other"
    assert result.source == "low_margin_rule"
    assert result.confidence == 0.0