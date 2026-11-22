"""Feature 1 orchestration: fetch -> validate -> parse -> structured result."""
from __future__ import annotations

from dataclasses import dataclass

from app.services.extraction.fetcher import fetch_html
from app.services.extraction.parser import ParsedContent, parse_html


@dataclass(frozen=True)
class ExtractionResult:
    requested_url: str
    final_url: str
    status_code: int
    content: ParsedContent


def extract_content(url: str) -> ExtractionResult:
    fetch_result = fetch_html(url)
    parsed = parse_html(fetch_result.html, url=fetch_result.final_url)
    return ExtractionResult(
        requested_url=fetch_result.url,
        final_url=fetch_result.final_url,
        status_code=fetch_result.status_code,
        content=parsed,
    )
