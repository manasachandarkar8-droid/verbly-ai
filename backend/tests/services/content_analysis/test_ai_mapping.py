
from app.schemas.content_analysis_ai import ContentAnalysisAIResponse
from app.services.content_analysis.ai_mapping import map_ai_response


def make_response(**overrides):
    data = {
        "summary_sentence_indices": [1, 3],
        "topics": [
            {"phrase": "machine learning", "score": 0.95},
            {"phrase": "artificial intelligence", "score": 0.90},
        ],
        "key_concepts": [
            {"phrase": "neural networks", "score": 0.88},
        ],
        "entities": [
            {"text": "Bangalore", "label": "LOC"},
            {"text": "OpenAI", "label": "ORG"},
        ],
        "intent_scores": [
            {"label": "informational", "score": 0.80},
            {"label": "commercial", "score": 0.10},
            {"label": "transactional", "score": 0.05},
            {"label": "navigational", "score": 0.05},
        ],
        "semantic_metrics": {
            "semantic_coherence": 0.90,
            "semantic_redundancy": 0.20,
            "concept_diversity": 0.75,
        },
    }

    data.update(overrides)
    return ContentAnalysisAIResponse.model_validate(data)


def test_summary_uses_exact_source_sentences():
    sentences = [
        "First sentence.",
        "Second sentence.",
        "Third sentence.",
        "Fourth sentence.",
        "Fifth sentence.",
        "Sixth sentence.",
    ]

    result = map_ai_response(
        make_response(),
        source_text=" ".join(sentences),
        sentences=sentences,
    )

    assert result["summary"] == [
        "Second sentence.",
        "Fourth sentence.",
    ]


def test_short_content_returns_all_source_sentences():
    sentences = [
        "First sentence.",
        "Second sentence.",
    ]

    result = map_ai_response(
        make_response(summary_sentence_indices=[]),
        source_text=" ".join(sentences),
        sentences=sentences,
    )

    assert result["summary"] == sentences


def test_invalid_summary_indices_are_ignored():
    sentences = [
        "One.",
        "Two.",
        "Three.",
        "Four.",
        "Five.",
        "Six.",
    ]

    result = map_ai_response(
        make_response(summary_sentence_indices=[1, 99]),
        source_text=" ".join(sentences),
        sentences=sentences,
    )

    assert result["summary"] == ["Two."]
    assert "invalid_summary_sentence_index" in result["warnings"]


def test_topics_are_source_grounded():
    result = map_ai_response(
        make_response(
            topics=[
                {"phrase": "machine learning", "score": 0.95},
                {"phrase": "unicorn technology", "score": 0.90},
            ]
        ),
        source_text="Machine learning is useful.",
        sentences=["Machine learning is useful."],
    )

    assert len(result["topics"]) == 1
    assert result["topics"][0]["phrase"] == "machine learning"
    assert "unsupported_ai_phrase_omitted" in result["warnings"]


def test_duplicate_topics_are_removed():
    result = map_ai_response(
        make_response(
            topics=[
                {"phrase": "Machine Learning", "score": 0.95},
                {"phrase": "machine learning", "score": 0.80},
            ]
        ),
        source_text="Machine learning is useful.",
        sentences=["Machine learning is useful."],
    )

    assert len(result["topics"]) == 1


def test_key_concepts_are_source_grounded():
    result = map_ai_response(
        make_response(
            key_concepts=[
                {"phrase": "neural networks", "score": 0.90},
                {"phrase": "quantum teleportation", "score": 0.80},
            ]
        ),
        source_text="Neural networks process information.",
        sentences=["Neural networks process information."],
    )

    assert len(result["key_concepts"]) == 1
    assert result["key_concepts"][0]["phrase"] == "neural networks"


def test_entity_offsets_are_calculated_from_source():
    source = "OpenAI develops artificial intelligence."

    result = map_ai_response(
        make_response(
            entities=[
                {"text": "OpenAI", "label": "ORG"},
            ]
        ),
        source_text=source,
        sentences=[source],
    )

    entity = result["entities"][0]

    assert entity["text"] == "OpenAI"
    assert entity["label"] == "ORG"
    assert source[entity["start"]:entity["end"]] == "OpenAI"


def test_bangalore_alias_is_preserved():
    source = "Bangalore is a technology hub."

    result = map_ai_response(
        make_response(
            entities=[
                {"text": "Bangalore", "label": "LOC"},
            ]
        ),
        source_text=source,
        sentences=[source],
    )

    assert result["entities"][0]["label"] == "GPE"


def test_unsupported_entities_are_ignored():
    source = "OpenAI develops AI."

    result = map_ai_response(
        make_response(
            entities=[
                {"text": "Atlantis", "label": "LOC"},
            ]
        ),
        source_text=source,
        sentences=[source],
    )

    assert result["entities"] == []
    assert "unsupported_entity_omitted" in result["warnings"]


def test_duplicate_entities_are_removed():
    source = "OpenAI develops AI."

    result = map_ai_response(
        make_response(
            entities=[
                {"text": "OpenAI", "label": "ORG"},
                {"text": "OpenAI", "label": "ORG"},
            ]
        ),
        source_text=source,
        sentences=[source],
    )

    assert len(result["entities"]) == 1


def test_intent_is_ranked_deterministically():
    result = map_ai_response(
        make_response(),
        source_text="Machine learning is useful.",
        sentences=["Machine learning is useful."],
    )

    intent = result["content_intent"]

    assert intent["label"] == "informational"
    assert intent["confidence"] == 0.8
    assert intent["source"] == "llm_estimate"
    assert len(intent["alternatives"]) == 3


def test_semantic_metrics_are_mapped():
    result = map_ai_response(
        make_response(),
        source_text="Machine learning is useful.",
        sentences=[
            "Machine learning is useful.",
            "AI helps analyse information.",
        ],
    )

    metrics = result["semantic_metrics"]

    assert metrics["semantic_coherence"] == 0.9
    assert metrics["semantic_redundancy"] == 0.2
    assert metrics["concept_diversity"] == 0.75
    assert metrics["analyzed_sentences"] == 2


def test_mapper_returns_expected_fields():
    result = map_ai_response(
        make_response(),
        source_text="Machine learning and neural networks.",
        sentences=["Machine learning and neural networks."],
    )

    expected = {
        "summary",
        "topics",
        "key_concepts",
        "entities",
        "content_intent",
        "semantic_metrics",
        "warnings",
    }

    assert set(result.keys()) == expected
