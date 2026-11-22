from __future__ import annotations

from fastapi import APIRouter

from app.schemas.readability import ReadabilityRequest, ReadabilityResponse
from app.services.readability.service import analyze_readability

router = APIRouter()


@router.post("/readability", response_model=ReadabilityResponse)
def create_readability_analysis(payload: ReadabilityRequest) -> ReadabilityResponse:
    result = analyze_readability(payload.text)

    return ReadabilityResponse(
        word_count=result.word_count,
        sentence_count=result.sentence_count,
        character_count=result.character_count,
        average_words_per_sentence=result.average_words_per_sentence,
        average_syllables_per_word=result.average_syllables_per_word,
        flesch_reading_ease=result.flesch_reading_ease,
        flesch_kincaid_grade=result.flesch_kincaid_grade,
        reading_level=result.reading_level,
    )
