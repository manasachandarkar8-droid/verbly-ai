from __future__ import annotations

from app.services.content_analysis.entities import extract_entities
from app.services.content_analysis.model_manager import ModelManager


def test_extract_entities_returns_named_entities() -> None:
    manager = ModelManager()

    text = (
        "Apple announced a new product in California. "
        "Tim Cook spoke at the event."
    )

    entities = extract_entities(text, manager)

    assert entities

    entity_pairs = {
        (entity.text, entity.label)
        for entity in entities
    }

    assert any(
        text == "Apple" and label == "ORG"
        for text, label in entity_pairs
    )

    assert any(
        text == "California" and label == "GPE"
        for text, label in entity_pairs
    )


def test_extract_entities_returns_sorted_offsets() -> None:
    manager = ModelManager()

    text = "Google operates in California."

    entities = extract_entities(text, manager)

    assert entities

    starts = [entity.start for entity in entities]

    assert starts == sorted(starts)


def test_extract_entities_contains_valid_offsets() -> None:
    manager = ModelManager()

    text = "Microsoft is based in Washington."

    entities = extract_entities(text, manager)

    for entity in entities:
        assert 0 <= entity.start < entity.end <= len(text)
        assert text[entity.start:entity.end] == entity.text


def test_empty_text_returns_empty_list() -> None:
    manager = ModelManager()

    assert extract_entities("", manager) == []
    assert extract_entities("   ", manager) == []

def test_bangalore_is_recognized_as_a_location() -> None:
    manager = ModelManager()

    text = "Bangalore is a city in India."

    entities = extract_entities(text, manager)

    bangalore_entities = [
        entity
        for entity in entities
        if entity.text == "Bangalore"
    ]

    assert len(bangalore_entities) == 1
    assert bangalore_entities[0].label == "GPE"


def test_ai_abbreviation_is_not_misclassified_as_named_entity() -> None:
    manager = ModelManager()

    text = (
        "Artificial intelligence is transforming healthcare. "
        "AI helps hospitals analyze medical images. "
        "Organizations must consider AI reliability and data privacy."
    )

    entities = extract_entities(text, manager)

    ai_entities = [
        entity
        for entity in entities
        if entity.text.casefold() == "ai"
    ]

    assert ai_entities == []


def test_ai_solutions_remains_a_named_organization() -> None:
    manager = ModelManager()

    text = "AI Solutions opened an office in Bangalore."

    entities = extract_entities(text, manager)

    assert any(
        entity.text == "AI Solutions" and entity.label == "ORG"
        for entity in entities
    )

def test_ordinary_technical_terms_are_not_named_entities() -> None:
    manager = ModelManager()

    text = (
        "Healthcare organizations protect patient data. "
        "AI systems analyze medical images."
    )

    entities = extract_entities(text, manager)

    ordinary_terms = {"healthcare", "ai"}

    assert not any(
        entity.text.casefold() in ordinary_terms
        and entity.label in {"ORG", "GPE"}
        for entity in entities
    )


def test_legitimate_organization_names_are_preserved() -> None:
    manager = ModelManager()

    text = (
        "Healthcare Inc. announced a new service. "
        "AI Solutions opened an office in Bangalore."
    )

    entities = extract_entities(text, manager)

    organizations = {
        entity.text
        for entity in entities
        if entity.label == "ORG"
    }

    assert "Healthcare Inc." in organizations
    assert "AI Solutions" in organizations

def test_hyphenated_technical_modifier_is_not_a_named_entity() -> None:
    manager = ModelManager()

    text = "Hospitals are adopting AI-powered systems to improve patient care."

    entities = extract_entities(text, manager)

    assert not any(
        entity.text.casefold() == "ai"
        and entity.label in {"ORG", "GPE"}
        for entity in entities
    )
