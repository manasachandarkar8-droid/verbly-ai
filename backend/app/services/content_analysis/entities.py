from __future__ import annotations

from dataclasses import dataclass

from spacy.tokens import Doc, Span

from app.services.content_analysis.model_manager import ModelManager


# Explicit, reviewed aliases for locations that spaCy may misclassify.
_LOCATION_ALIASES: dict[str, str] = {
    "bangalore": "GPE",
}


@dataclass(frozen=True)
class EntityResult:
    text: str
    label: str
    start: int
    end: int


def _is_attributive_single_token_entity(
    entity: Span,
    doc: Doc,
) -> bool:
    """
    Filter likely false-positive single-token ORG/GPE predictions
    used as attributive modifiers.

    Supports direct noun modifiers and hyphenated compounds.
    Multi-token organization names remain untouched.
    """
    if entity.label_ not in {"ORG", "GPE"}:
        return False

    if len(entity) != 1 or entity.end >= len(doc):
        return False

    following_token = doc[entity.end]

    # Example: "AI systems"
    if following_token.pos_ == "NOUN":
        return True

    # Example: "AI-powered systems"
    if following_token.is_punct and following_token.text in {
        "-", "‐", "‒", "–", "—",
    }:
        modifier_index = entity.end + 1

        if modifier_index >= len(doc):
            return False

        modifier = doc[modifier_index]
        head_index = modifier_index + 1

        if (
            modifier.pos_ in {"ADJ", "VERB"}
            and head_index < len(doc)
            and doc[head_index].pos_ == "NOUN"
        ):
            return True

    return False


def extract_entities(
    text: str,
    model_manager: ModelManager,
) -> list[EntityResult]:
    """
    Extract named entities using spaCy.

    Apply a contextual filter to some single-token ORG/GPE false positives,
    normalize reviewed location aliases, and preserve source-text offsets.
    """
    if not text.strip():
        return []

    doc = model_manager.nlp(text)
    entities: list[EntityResult] = []

    for entity in doc.ents:
        if _is_attributive_single_token_entity(entity, doc):
            continue

        entities.append(
            EntityResult(
                text=entity.text,
                label=_LOCATION_ALIASES.get(
                    entity.text.casefold(),
                    entity.label_,
                ),
                start=entity.start_char,
                end=entity.end_char,
            )
        )

    entities.sort(
        key=lambda entity: (
            entity.start,
            entity.end,
            entity.label,
            entity.text.casefold(),
        )
    )

    return entities