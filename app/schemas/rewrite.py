from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


MAX_REWRITE_CHARACTERS = 200_000
MAX_CUSTOM_INSTRUCTION_CHARACTERS = 2_000

RewriteTone = Literal[
    "concise",
    "professional",
    "friendly",
    "seo-optimized",
]


class RewriteRequest(BaseModel):
    main_text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_REWRITE_CHARACTERS,
        description="The original content to rewrite.",
    )

    tone: RewriteTone = Field(
        default="concise",
        description="The desired writing tone.",
    )

    custom_instruction: str | None = Field(
        default=None,
        max_length=MAX_CUSTOM_INSTRUCTION_CHARACTERS,
        description="Optional additional rewriting guidance.",
    )

    @field_validator("main_text")
    @classmethod
    def validate_main_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Content must not be empty or whitespace only.")

        return value

    @field_validator("custom_instruction")
    @classmethod
    def validate_custom_instruction(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()

        if not normalized_value:
            return None

        return normalized_value


class RewriteResponse(BaseModel):
    rewritten_text: str = Field(
        ...,
        min_length=1,
        description="The rewritten content.",
    )