"""Main-content extraction from raw HTML using trafilatura."""
from __future__ import annotations

import json
from dataclasses import dataclass

import trafilatura
from trafilatura.settings import use_config

from app.services.extraction.exceptions import InsufficientContentError

_MIN_CONTENT_CHARACTERS = 50

# Disable trafilatura's own disk signal file (not needed, avoids noisy
# warnings / filesystem writes in a stateless API service).
_TRAFILATURA_CONFIG = use_config()
_TRAFILATURA_CONFIG.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")


@dataclass(frozen=True)
class ParsedContent:
    title: str | None
    author: str | None
    description: str | None
    site_name: str | None
    published_date: str | None
    main_text: str
    word_count: int
    character_count: int


def parse_html(html: str, *, url: str | None = None) -> ParsedContent:
    """
    Extract the main readable content and metadata from ``html``.
    Raises ``InsufficientContentError`` if too little meaningful content
    could be found (e.g. a JS-only shell page, or an error page).
    """
    extracted_json = trafilatura.extract(
        html,
        url=url,
        output_format="json",
        with_metadata=True,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
        config=_TRAFILATURA_CONFIG,
    )

    if not extracted_json:
        raise InsufficientContentError(
            "No meaningful main content could be extracted from this page."
        )

    data = json.loads(extracted_json)
    main_text = (data.get("text") or "").strip()

    if len(main_text) < _MIN_CONTENT_CHARACTERS:
        raise InsufficientContentError(
            "The extracted content was too short to be meaningful."
        )

    word_count = len(main_text.split())
    character_count = len(main_text)

    return ParsedContent(
        title=data.get("title") or None,
        author=data.get("author") or None,
        description=data.get("description") or None,
        site_name=data.get("sitename") or None,
        published_date=data.get("date") or None,
        main_text=main_text,
        word_count=word_count,
        character_count=character_count,
    )
