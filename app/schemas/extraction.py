from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class ExtractionRequest(BaseModel):
    url: HttpUrl = Field(..., description="The webpage URL to fetch and extract content from.")


class ExtractionResponse(BaseModel):
    requested_url: str
    final_url: str
    status_code: int
    title: str | None = None
    author: str | None = None
    description: str | None = None
    site_name: str | None = None
    published_date: str | None = None
    main_text: str
    word_count: int
    character_count: int


class ExtractionErrorResponse(BaseModel):
    error: str
    detail: str
