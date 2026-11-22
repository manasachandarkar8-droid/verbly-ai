from __future__ import annotations

from pydantic import BaseModel, Field


MAX_REQUEST_CHARACTERS = 200_000


class ContentAnalysisRequest(BaseModel):
    main_text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_REQUEST_CHARACTERS,
        description="Main textual content to analyze.",
    )

    title: str | None = Field(
        default=None,
        max_length=1_000,
        description="Optional page title.",
    )

    description: str | None = Field(
        default=None,
        max_length=5_000,
        description="Optional page meta description.",
    )

class SummaryItem(BaseModel):
    text: str


class TopicItem(BaseModel):
    phrase: str
    score: float = Field(ge=0.0, le=1.0)


class KeyConceptItem(BaseModel):
    phrase: str
    score: float = Field(ge=0.0, le=1.0)


class EntityItem(BaseModel):
    text: str
    label: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class IntentAlternative(BaseModel):
    label: str
    score: float = Field(ge=0.0, le=1.0)


class ContentIntent(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str
    alternatives: list[IntentAlternative]


class ContentStructure(BaseModel):
    paragraph_count: int = Field(ge=0)
    sentence_count: int = Field(ge=0)
    average_words_per_sentence: float = Field(ge=0.0)
    shortest_sentence_words: int = Field(ge=0)
    longest_sentence_words: int = Field(ge=0)
    short_sentence_count: int = Field(ge=0)
    long_sentence_count: int = Field(ge=0)
    heading_like_count: int = Field(ge=0)
    list_item_count: int = Field(ge=0)


class QualitySignals(BaseModel):
    word_count: int = Field(ge=0)
    unique_word_count: int = Field(ge=0)
    vocabulary_diversity: float = Field(ge=0.0, le=1.0)
    repeated_word_ratio: float = Field(ge=0.0, le=1.0)
    average_words_per_sentence: float = Field(ge=0.0)
    short_content: bool
    repetitive_content: bool
    english_likelihood: float = Field(ge=0.0, le=1.0)
    warnings: list[str]


class SemanticMetrics(BaseModel):
    semantic_coherence: float = Field(ge=0.0, le=1.0)
    semantic_redundancy: float = Field(ge=0.0, le=1.0)
    concept_diversity: float = Field(ge=0.0, le=1.0)
    analyzed_sentences: int = Field(ge=0)


class AnalysisWindow(BaseModel):
    received_characters: int = Field(ge=0)
    original_characters: int = Field(ge=0)
    analyzed_characters: int = Field(ge=0)
    analyzed_sentences: int = Field(ge=0)
    truncated: bool
    truncation_reason: str | None = None


class ContentAnalysisResponse(BaseModel):
    summary: list[SummaryItem]
    topics: list[TopicItem]
    key_concepts: list[KeyConceptItem]
    entities: list[EntityItem]
    content_intent: ContentIntent
    content_structure: ContentStructure
    quality_signals: QualitySignals
    semantic_metrics: SemanticMetrics
    analysis_window: AnalysisWindow
    warnings: list[str]    