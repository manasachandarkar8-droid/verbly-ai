from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


IntentLabel = Literal[
    "informational",
    "commercial",
    "transactional",
    "navigational",
]

EntityLabel = Literal[
    "PERSON",
    "ORG",
    "GPE",
    "LOC",
    "PRODUCT",
    "EVENT",
    "WORK_OF_ART",
    "LAW",
    "NORP",
    "FAC",
]


class AIBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class AITopicItem(AIBaseModel):
    phrase: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)


class AIKeyConceptItem(AIBaseModel):
    phrase: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)


class AIEntityMention(AIBaseModel):
    text: str = Field(min_length=1)
    label: EntityLabel


class AIIntentScore(AIBaseModel):
    label: IntentLabel
    score: float = Field(ge=0.0, le=1.0)


class AISemanticMetrics(AIBaseModel):
    semantic_coherence: float = Field(ge=0.0, le=1.0)
    semantic_redundancy: float = Field(ge=0.0, le=1.0)
    concept_diversity: float = Field(ge=0.0, le=1.0)


class ContentAnalysisAIResponse(AIBaseModel):
    summary_sentence_indices: list[
        Annotated[int, Field(ge=0)]
    ] = Field(max_length=5)

    topics: list[AITopicItem] = Field(max_length=10)

    key_concepts: list[AIKeyConceptItem] = Field(
        max_length=20
    )

    entities: list[AIEntityMention]

    intent_scores: list[AIIntentScore] = Field(
        min_length=4,
        max_length=4,
    )

    semantic_metrics: AISemanticMetrics

    @model_validator(mode="after")
    def validate_response(self) -> ContentAnalysisAIResponse:

        # Summary indices must be unique.
        if len(set(self.summary_sentence_indices)) != len(
            self.summary_sentence_indices
        ):
            raise ValueError(
                "Summary sentence indices must be unique."
            )

        # All four supported intent categories must appear.
        labels = [
            item.label
            for item in self.intent_scores
        ]

        expected_labels = {
            "informational",
            "commercial",
            "transactional",
            "navigational",
        }

        if len(set(labels)) != 4:
            raise ValueError(
                "Intent scores must contain four unique categories."
            )

        if set(labels) != expected_labels:
            raise ValueError(
                "Intent scores must contain all four supported categories."
            )

        return self