from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.schemas.content_analysis_ai import ContentAnalysisAIResponse
from app.services.ai.provider import (
    AIProviderDeadlineExceededError,
    AIProviderUnavailableError,
)
from app.services.content_analysis.service import ContentAnalysisService


def make_ai_response() -> ContentAnalysisAIResponse:
    return ContentAnalysisAIResponse.model_validate({
        "summary_sentence_indices": [0],
        "topics": [
            {
                "phrase": "Artificial intelligence",
                "score": 0.95,
            }
        ],
        "key_concepts": [
            {
                "phrase": "Machine learning",
                "score": 0.91,
            }
        ],
        "entities": [
            {
                "text": "Artificial intelligence",
                "label": "PRODUCT",
            }
        ],
        "intent_scores": [
            {"label": "informational", "score": 0.85},
            {"label": "commercial", "score": 0.05},
            {"label": "transactional", "score": 0.05},
            {"label": "navigational", "score": 0.05},
        ],
        "semantic_metrics": {
            "semantic_coherence": 0.91,
            "semantic_redundancy": 0.02,
            "concept_diversity": 0.72,
        },
    })


def make_service():
    service = ContentAnalysisService()
    provider = Mock()
    provider.analyze.return_value = make_ai_response()
    service._ai_provider = provider
    return service, provider


def test_content_analysis_service_returns_structured_result():
    service, provider = make_service()

    result = service.analyze(
        main_text=(
            "Artificial intelligence helps organizations analyze data. "
            "Machine learning identifies useful patterns."
        ),
        title="AI Analysis",
        description="Artificial intelligence analysis.",
    )

    assert result.summary
    assert result.summary[0]["text"] == (
        "Artificial intelligence helps organizations analyze data."
    )

    assert result.topics[0]["phrase"] == "Artificial intelligence"
    assert result.key_concepts[0]["phrase"] == "Machine learning"

    assert result.entities[0]["text"] == "Artificial intelligence"
    assert result.entities[0]["start"] == 0

    assert result.content_intent["label"] == "informational"
    assert result.content_intent["source"] == "llm_estimate"

    assert result.content_structure["sentence_count"] == 2
    assert result.quality_signals["word_count"] > 0

    assert result.semantic_metrics["semantic_coherence"] == 0.91
    assert result.semantic_metrics["concept_diversity"] == 0.72

    assert result.analysis_window.received_characters > 0
    assert result.analysis_window.truncated is False

    provider.analyze.assert_called_once()


def test_service_reports_truncation_warning(monkeypatch):
    service, provider = make_service()

    from app.services.content_analysis import service as service_module

    monkeypatch.setattr(
        service_module,
        "preprocess_text",
        lambda text: SimpleNamespace(
            text="Short text.",
            sentences=["Short text."],
            received_characters=100,
            original_characters=100,
            analyzed_characters=11,
            truncated=True,
            truncation_reason="characters",
        ),
    )

    result = service.analyze(main_text="x" * 100)

    assert result.analysis_window.truncated is True
    assert result.analysis_window.truncation_reason == "characters"
    assert "analysis_truncated:characters" in result.warnings

    provider.analyze.assert_called_once()


def test_service_returns_partial_result_when_deadline_expires(
    monkeypatch,
):
    service, provider = make_service()

    from app.services.content_analysis import service as service_module

    ticks = iter([0.0, 2.0])

    monkeypatch.setattr(
        service_module,
        "get_settings",
        lambda: SimpleNamespace(
            content_analysis_deadline_seconds=1.0
        ),
    )

    monkeypatch.setattr(
        service_module,
        "monotonic",
        lambda: next(ticks),
    )

    result = service.analyze(
        main_text="Artificial intelligence helps organizations."
    )

    assert result.summary == []
    assert result.topics == []
    assert result.key_concepts == []
    assert result.entities == []

    assert result.content_intent["source"] == "deadline_exceeded"

    # Deterministic analysis must still be available.
    assert result.content_structure["sentence_count"] > 0
    assert result.quality_signals["word_count"] > 0

    assert result.analysis_window.truncated is True
    assert result.analysis_window.truncation_reason == "deadline"

    assert "analysis_deadline_exceeded" in result.warnings

    provider.analyze.assert_not_called()


def test_service_preserves_deterministic_results_when_provider_deadline_expires():
    service, provider = make_service()

    provider.analyze.side_effect = AIProviderDeadlineExceededError(
        "Analysis deadline expired."
    )

    result = service.analyze(
        main_text=(
            "Artificial intelligence helps organizations "
            "analyze information."
        )
    )

    assert result.summary == []
    assert result.topics == []
    assert result.key_concepts == []
    assert result.entities == []

    assert result.content_intent["source"] == "deadline_exceeded"

    assert result.content_structure["sentence_count"] > 0
    assert result.quality_signals["word_count"] > 0

    assert result.analysis_window.truncated is True
    assert result.analysis_window.truncation_reason == "deadline"

    assert "analysis_deadline_exceeded" in result.warnings

    provider.analyze.assert_called_once()


def test_service_propagates_provider_unavailable_error():
    service, provider = make_service()

    provider.analyze.side_effect = AIProviderUnavailableError(
        "Both providers are unavailable."
    )

    with pytest.raises(AIProviderUnavailableError):
        service.analyze(
            main_text="Artificial intelligence helps organizations."
        )

    provider.analyze.assert_called_once()