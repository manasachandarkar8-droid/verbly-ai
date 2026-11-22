import pytest
from pydantic import ValidationError

from app.schemas.content_analysis_ai import (
    ContentAnalysisAIResponse,
)
from pydantic import ValidationError


@pytest.fixture
def valid_ai_response():
    return {
        "summary_sentence_indices": [0, 2],
        "topics": [
            {"phrase": "artificial intelligence", "score": 0.95}
        ],
        "key_concepts": [
            {"phrase": "machine learning", "score": 0.91}
        ],
        "entities": [
            {"text": "Bangalore", "label": "GPE"}
        ],
        "intent_scores": [
            {"label": "informational", "score": 0.85},
            {"label": "commercial", "score": 0.05},
            {"label": "transactional", "score": 0.05},
            {"label": "navigational", "score": 0.05},
        ],
        "semantic_metrics": {
            "semantic_coherence": 0.85,
            "semantic_redundancy": 0.15,
            "concept_diversity": 0.75,
        },
    }


def test_valid_ai_response_is_accepted(valid_ai_response):
    result = ContentAnalysisAIResponse.model_validate(
        valid_ai_response
    )

    assert result.intent_scores[0].label == "informational"
    assert result.semantic_metrics.semantic_coherence == 0.85


def test_missing_required_field_is_rejected(valid_ai_response):
    del valid_ai_response["summary_sentence_indices"]

    with pytest.raises(ValidationError):
        ContentAnalysisAIResponse.model_validate(
            valid_ai_response
        )


def test_invalid_semantic_score_is_rejected(valid_ai_response):
    valid_ai_response["semantic_metrics"][
        "semantic_coherence"
    ] = 1.5

    with pytest.raises(ValidationError):
        ContentAnalysisAIResponse.model_validate(
            valid_ai_response
        )


def test_negative_topic_score_is_rejected(valid_ai_response):
    valid_ai_response["topics"][0]["score"] = -0.1

    with pytest.raises(ValidationError):
        ContentAnalysisAIResponse.model_validate(
            valid_ai_response
        )


def test_unsupported_intent_label_is_rejected(valid_ai_response):
    valid_ai_response["intent_scores"][0]["label"] = "mixed/other"

    with pytest.raises(ValidationError):
        ContentAnalysisAIResponse.model_validate(
            valid_ai_response
        )


def test_duplicate_intent_categories_are_rejected(valid_ai_response):
    valid_ai_response["intent_scores"][1]["label"] = "informational"

    with pytest.raises(ValidationError):
        ContentAnalysisAIResponse.model_validate(
            valid_ai_response
        )


def test_missing_intent_category_is_rejected(valid_ai_response):
    valid_ai_response["intent_scores"] = (
        valid_ai_response["intent_scores"][:3]
    )

    with pytest.raises(ValidationError):
        ContentAnalysisAIResponse.model_validate(
            valid_ai_response
        )


def test_extra_root_field_is_rejected(valid_ai_response):
    valid_ai_response["unexpected_field"] = "not allowed"

    with pytest.raises(ValidationError):
        ContentAnalysisAIResponse.model_validate(
            valid_ai_response
        )


def test_extra_nested_field_is_rejected(valid_ai_response):
    valid_ai_response["entities"][0]["start"] = 10

    with pytest.raises(ValidationError):
        ContentAnalysisAIResponse.model_validate(
            valid_ai_response
        )


def test_empty_entity_text_is_rejected(valid_ai_response):
    valid_ai_response["entities"][0]["text"] = ""

    with pytest.raises(ValidationError):
        ContentAnalysisAIResponse.model_validate(
            valid_ai_response
        )


def test_negative_summary_index_is_rejected(valid_ai_response):
    valid_ai_response["summary_sentence_indices"] = [-1]

    with pytest.raises(ValidationError):
        ContentAnalysisAIResponse.model_validate(
            valid_ai_response
        )


def test_score_boundaries_are_accepted(valid_ai_response):
    valid_ai_response["topics"][0]["score"] = 0.0
    valid_ai_response["key_concepts"][0]["score"] = 1.0

    result = ContentAnalysisAIResponse.model_validate(
        valid_ai_response
    )

    assert result.topics[0].score == 0.0
    assert result.key_concepts[0].score == 1.0


def test_json_schema_rejects_additional_properties():
    schema = ContentAnalysisAIResponse.model_json_schema()

    assert schema["additionalProperties"] is False


def test_json_schema_contains_all_required_ai_fields():
    schema = ContentAnalysisAIResponse.model_json_schema()

    required_fields = set(schema["required"])

    assert required_fields == {
    "summary_sentence_indices",
    "topics",
    "key_concepts",
    "entities",
    "intent_scores",
    "semantic_metrics",
}

def test_duplicate_summary_indices_are_rejected(valid_ai_response):
    valid_ai_response["summary_sentence_indices"] = [0, 2, 2]

    with pytest.raises(ValidationError):
        ContentAnalysisAIResponse.model_validate(
            valid_ai_response
        )


def test_more_than_five_summary_indices_are_rejected(valid_ai_response):
    valid_ai_response["summary_sentence_indices"] = [
        0, 1, 2, 3, 4, 5
    ]

    with pytest.raises(ValidationError):
        ContentAnalysisAIResponse.model_validate(
            valid_ai_response
        )


def test_empty_summary_indices_are_accepted(valid_ai_response):
    valid_ai_response["summary_sentence_indices"] = []

    result = ContentAnalysisAIResponse.model_validate(
        valid_ai_response
    )

    assert result.summary_sentence_indices == []    