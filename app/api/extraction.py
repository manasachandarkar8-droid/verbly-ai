from __future__ import annotations

from fastapi import APIRouter

from app.schemas.extraction import ExtractionRequest, ExtractionResponse
from app.services.extraction.service import extract_content

router = APIRouter()


@router.post("/extraction", response_model=ExtractionResponse)
def create_extraction(payload: ExtractionRequest) -> ExtractionResponse:
    # Any ExtractionError subclass raised here is caught by the centralized
    # handler registered in app.core.exceptions (see register_exception_handlers
    # in app.main), which maps it to the appropriate HTTP status code.
    result = extract_content(str(payload.url))

    content = result.content
    return ExtractionResponse(
        requested_url=result.requested_url,
        final_url=result.final_url,
        status_code=result.status_code,
        title=content.title,
        author=content.author,
        description=content.description,
        site_name=content.site_name,
        published_date=content.published_date,
        main_text=content.main_text,
        word_count=content.word_count,
        character_count=content.character_count,
    )
