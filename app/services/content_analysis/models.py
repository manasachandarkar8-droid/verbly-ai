from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisWindow:
    received_characters: int
    original_characters: int
    analyzed_characters: int
    analyzed_sentences: int
    truncated: bool
    truncation_reason: str | None


@dataclass(frozen=True)
class ContentAnalysisResult:
    summary: list[str]
    topics: list[dict]
    key_concepts: list[dict]
    entities: list[dict]
    content_intent: dict
    content_structure: dict
    quality_signals: dict
    semantic_metrics: dict
    analysis_window: AnalysisWindow
    warnings: list[str]