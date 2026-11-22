from __future__ import annotations

from time import monotonic

from app.core.config import get_settings

from app.schemas.content_analysis_ai import ContentAnalysisAIResponse

from app.services.ai.factory import get_ai_provider
from app.services.ai.provider import AIProviderDeadlineExceededError

from app.services.content_analysis.ai_mapping import map_ai_response
from app.services.content_analysis.ai_prompts import build_analysis_messages

from app.services.content_analysis.models import (
    AnalysisWindow,
    ContentAnalysisResult,
)

from app.services.content_analysis.preprocessing import preprocess_text
from app.services.content_analysis.quality import analyze_quality
from app.services.content_analysis.structure import analyze_structure


class ContentAnalysisService:
    """
    Coordinate deterministic content analysis and AI-powered analysis.

    Structure and quality calculations are performed locally.
    Semantic analysis, summarization, topics, concepts, entities
    and intent classification are handled by the AI provider.

    Groq is the primary provider and Cloudflare is the backup.
    """

    def __init__(self) -> None:
        self._ai_provider = get_ai_provider()

    @staticmethod
    def _empty_intent() -> dict:
        return {
            "label": "mixed/other",
            "confidence": 0.0,
            "source": "deadline_exceeded",
            "alternatives": [],
        }

    @staticmethod
    def _empty_semantic() -> dict:
        return {
            "semantic_coherence": 0.0,
            "semantic_redundancy": 0.0,
            "concept_diversity": 0.0,
            "analyzed_sentences": 0,
        }

    @staticmethod
    def _structure_to_dict(result) -> dict:
        return {
            "paragraph_count": result.paragraph_count,
            "sentence_count": result.sentence_count,
            "average_words_per_sentence": (
                result.average_words_per_sentence
            ),
            "shortest_sentence_words": result.shortest_sentence_words,
            "longest_sentence_words": result.longest_sentence_words,
            "short_sentence_count": result.short_sentence_count,
            "long_sentence_count": result.long_sentence_count,
            "heading_like_count": result.heading_like_count,
            "list_item_count": result.list_item_count,
        }

    @staticmethod
    def _quality_to_dict(result) -> dict:
        return {
            "word_count": result.word_count,
            "unique_word_count": result.unique_word_count,
            "vocabulary_diversity": result.vocabulary_diversity,
            "repeated_word_ratio": result.repeated_word_ratio,
            "average_words_per_sentence": (
                result.average_words_per_sentence
            ),
            "short_content": result.short_content,
            "repetitive_content": result.repetitive_content,
            "english_likelihood": result.english_likelihood,
            "warnings": list(result.warnings),
        }

    def analyze(
        self,
        main_text: str,
        title: str | None = None,
        description: str | None = None,
    ) -> ContentAnalysisResult:

        settings = get_settings()

        deadline = (
            monotonic() + settings.content_analysis_deadline_seconds
        )

        # --------------------------------------------------
        # 1. Preprocessing
        # --------------------------------------------------

        preprocessed = preprocess_text(main_text)

        # --------------------------------------------------
        # 2. Deterministic structural analysis
        # --------------------------------------------------

        structure_result = analyze_structure(
            text=preprocessed.text,
            sentences=preprocessed.sentences,
        )

        structure = self._structure_to_dict(structure_result)

        # --------------------------------------------------
        # 3. Deterministic quality analysis
        # --------------------------------------------------

        quality_result = analyze_quality(
            text=preprocessed.text,
            sentence_count=len(preprocessed.sentences),
            average_words_per_sentence=(
                structure["average_words_per_sentence"]
            ),
        )

        quality = self._quality_to_dict(quality_result)

        # --------------------------------------------------
        # 4. Initialize AI-dependent results
        # --------------------------------------------------

        summary: list[dict] = []
        topics: list[dict] = []
        key_concepts: list[dict] = []
        entities: list[dict] = []

        intent = self._empty_intent()
        semantic = self._empty_semantic()

        warnings = list(quality["warnings"])

        deadline_hit = False

        # --------------------------------------------------
        # 5. Check deadline before making an API request
        # --------------------------------------------------

        if monotonic() >= deadline:
            deadline_hit = True

        else:
            try:
                # ------------------------------------------
                # 6. Build AI messages
                # ------------------------------------------

                messages = build_analysis_messages(
                    text=preprocessed.text,
                    sentences=preprocessed.sentences,
                    title=title,
                    description=description,
                )

                # ------------------------------------------
                # 7. Generate the JSON schema
                # ------------------------------------------

                json_schema = (
                    ContentAnalysisAIResponse.model_json_schema()
                )

                # ------------------------------------------
                # 8. Call the primary/backup AI provider
                # ------------------------------------------

                ai_response = self._ai_provider.analyze(
                    messages=messages,
                    schema_name="verbly_content_analysis",
                    json_schema=json_schema,
                    deadline=deadline,
                )

                # ------------------------------------------
                # 9. Map AI response into internal fields
                # ------------------------------------------

                mapped = map_ai_response(
                    ai_response,
                    source_text=preprocessed.text,
                    sentences=preprocessed.sentences,
                )

                # Preserve the existing API summary format.
                summary = [
                    {"text": sentence}
                    for sentence in mapped["summary"]
                ]

                topics = mapped["topics"]
                key_concepts = mapped["key_concepts"]
                entities = mapped["entities"]

                intent = mapped["content_intent"]
                semantic = mapped["semantic_metrics"]

                warnings.extend(mapped["warnings"])

            except AIProviderDeadlineExceededError:
                deadline_hit = True

        # --------------------------------------------------
        # 10. Add truncation warnings
        # --------------------------------------------------

        if preprocessed.truncated:
            warnings.append(
                f"analysis_truncated:{preprocessed.truncation_reason}"
            )

        if deadline_hit:
            warnings.append("analysis_deadline_exceeded")

        # --------------------------------------------------
        # 11. Build analysis window
        # --------------------------------------------------

        analysis_window = AnalysisWindow(
            received_characters=preprocessed.received_characters,
            original_characters=preprocessed.original_characters,
            analyzed_characters=preprocessed.analyzed_characters,
            analyzed_sentences=len(preprocessed.sentences),
            truncated=preprocessed.truncated or deadline_hit,
            truncation_reason=(
                "deadline"
                if deadline_hit
                else preprocessed.truncation_reason
            ),
        )

        # --------------------------------------------------
        # 12. Return the existing internal result contract
        # --------------------------------------------------

        return ContentAnalysisResult(
            summary=summary,
            topics=topics,
            key_concepts=key_concepts,
            entities=entities,
            content_intent=intent,
            content_structure=structure,
            quality_signals=quality,
            semantic_metrics=semantic,
            analysis_window=analysis_window,
            warnings=list(dict.fromkeys(warnings)),
        )


_service = ContentAnalysisService()


def get_content_analysis_service() -> ContentAnalysisService:
    return _service