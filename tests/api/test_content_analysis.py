from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app

from app.services.ai.provider import (
    AIProviderConfigurationError,
    AIProviderQuotaExceededError,
    AIProviderPaidPlanRequiredError,
    AIProviderUnavailableError,
    AIProviderRequestError,
)

from app.services.content_analysis.models import (
    AnalysisWindow,
    ContentAnalysisResult,
)


client = TestClient(app)


def make_result() -> ContentAnalysisResult:
    return ContentAnalysisResult(
        summary=[
            {"text": "Artificial intelligence helps healthcare."}
        ],
        topics=[
            {
                "phrase": "Artificial intelligence",
                "score": 0.95,
            }
        ],
        key_concepts=[
            {
                "phrase": "Machine learning",
                "score": 0.91,
            }
        ],
        entities=[
            {
                "text": "Artificial intelligence",
                "label": "TECHNOLOGY",
                "start": 0,
                "end": 24,
            }
        ],
        content_intent={
            "label": "informational",
            "confidence": 0.85,
            "source": "llm_estimate",
            "alternatives": [
                {"label": "commercial", "score": 0.05},
                {"label": "transactional", "score": 0.05},
                {"label": "navigational", "score": 0.05},
            ],
        },
        content_structure={
            "paragraph_count": 1,
            "sentence_count": 2,
            "average_words_per_sentence": 7.5,
            "shortest_sentence_words": 5,
            "longest_sentence_words": 10,
            "short_sentence_count": 1,
            "long_sentence_count": 0,
            "heading_like_count": 0,
            "list_item_count": 0,
        },
        quality_signals={
            "word_count": 15,
            "unique_word_count": 13,
            "vocabulary_diversity": 0.8667,
            "repeated_word_ratio": 0.1333,
            "average_words_per_sentence": 7.5,
            "short_content": True,
            "repetitive_content": False,
            "english_likelihood": 1.0,
            "warnings": ["content_too_short"],
        },
        semantic_metrics={
            "semantic_coherence": 0.91,
            "semantic_redundancy": 0.02,
            "concept_diversity": 0.72,
            "analyzed_sentences": 2,
        },
        analysis_window=AnalysisWindow(
            received_characters=100,
            original_characters=100,
            analyzed_characters=100,
            analyzed_sentences=2,
            truncated=False,
            truncation_reason=None,
        ),
        warnings=["content_too_short"],
    )


def make_request() -> dict:
    return {
        "main_text": (
            "Artificial intelligence helps healthcare organizations "
            "analyze medical information. Machine learning identifies "
            "patterns that support better hospital operations. "
            "Natural language processing helps computers understand "
            "human language and extract useful information. "
            "These technologies can improve efficiency and help "
            "organizations make informed decisions."
        ),
        "title": "Artificial Intelligence in Healthcare",
        "description": (
            "An overview of AI, machine learning, and NLP in healthcare."
        ),
    }


def mock_service(monkeypatch, *, side_effect=None):
    service = Mock()

    if side_effect is None:
        service.analyze.return_value = make_result()
    else:
        service.analyze.side_effect = side_effect

    monkeypatch.setattr(
        "app.api.content_analysis.get_content_analysis_service",
        lambda: service,
    )

    return service


def test_content_analysis_rejects_empty_text():
    response = client.post(
        "/content-analysis",
        json={"main_text": ""},
    )

    assert response.status_code == 422


def test_content_analysis_rejects_text_over_request_limit():
    response = client.post(
        "/content-analysis",
        json={"main_text": "a" * 200_001},
    )

    assert response.status_code == 422


def test_content_analysis_rejects_invalid_request_type():
    response = client.post(
        "/content-analysis",
        json={"main_text": 123},
    )

    assert response.status_code == 422


def test_content_analysis_returns_valid_response(monkeypatch):
    service = mock_service(monkeypatch)

    response = client.post(
        "/content-analysis",
        json=make_request(),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert isinstance(data["summary"], list)
    assert isinstance(data["topics"], list)
    assert isinstance(data["key_concepts"], list)
    assert isinstance(data["entities"], list)

    assert data["summary"][0]["text"] == (
        "Artificial intelligence helps healthcare."
    )

    assert data["content_intent"]["label"] == "informational"
    assert data["content_intent"]["source"] == "llm_estimate"

    assert 0.0 <= data["content_intent"]["confidence"] <= 1.0

    assert "content_structure" in data
    assert "quality_signals" in data
    assert "semantic_metrics" in data
    assert "analysis_window" in data

    assert isinstance(data["warnings"], list)
    assert data["analysis_window"]["truncated"] is False

    service.analyze.assert_called_once()


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (
            AIProviderConfigurationError("configuration failure"),
            503,
        ),
        (
            AIProviderQuotaExceededError("quota exhausted"),
            503,
        ),
        (
            AIProviderPaidPlanRequiredError("paid plan required"),
            503,
        ),
        (
            AIProviderUnavailableError("providers unavailable"),
            503,
        ),
        (
            AIProviderRequestError("request rejected"),
            502,
        ),
    ],
)
def test_content_analysis_maps_provider_errors(
    monkeypatch,
    error,
    expected_status,
):
    mock_service(monkeypatch, side_effect=error)

    response = client.post(
        "/content-analysis",
        json=make_request(),
    )

    assert response.status_code == expected_status

    # Internal provider exception messages must not leak.
    assert str(error) not in response.text


def test_content_analysis_returns_busy_when_semaphore_unavailable(
    monkeypatch,
):
    semaphore = Mock()
    semaphore.acquire.return_value = False

    monkeypatch.setattr(
        "app.api.content_analysis._analysis_semaphore",
        semaphore,
    )

    response = client.post(
        "/content-analysis",
        json=make_request(),
    )

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"

    semaphore.acquire.assert_called_once()
    semaphore.release.assert_not_called()