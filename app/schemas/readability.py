from __future__ import annotations

from pydantic import BaseModel, Field

#: Upper bound on submitted text length. This is a stateless, CPU-bound
#: endpoint (no network calls), so the main resource-consumption risk is
#: an extremely large payload driving up request size/processing time;
#: 50,000 characters (roughly a long article or short chapter) is a
#: generous ceiling for a "content readability" use case while keeping
#: worst-case processing effectively instant.
MAX_TEXT_LENGTH = 50_000


class ReadabilityRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TEXT_LENGTH,
        description="The text content to analyze for readability.",
    )


class ReadabilityResponse(BaseModel):
    word_count: int
    sentence_count: int
    character_count: int
    average_words_per_sentence: float
    average_syllables_per_word: float
    flesch_reading_ease: float
    flesch_kincaid_grade: float
    reading_level: str
