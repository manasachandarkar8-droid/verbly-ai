from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

MAX_TEXT_LENGTH = 20_000

class GrammarRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)

    @field_validator("text")
    @classmethod
    def reject_whitespace_only(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must contain non-whitespace characters")
        return value

class GrammarFindingResult(BaseModel):
    message: str
    short_message: str | None
    category: str | None
    rule_id: str | None
    issue_type: str | None
    severity: str | None
    offset: int
    length: int
    context: str | None
    replacements: list[str]

class GrammarResponse(BaseModel):
    text_length: int
    finding_count: int
    findings: list[GrammarFindingResult]
    issues: list[str]
