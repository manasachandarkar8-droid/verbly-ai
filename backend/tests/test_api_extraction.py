from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.api.extraction as extraction_api
from app.main import app
from app.services.extraction.exceptions import (
    InsufficientContentError,
    SSRFBlockedError,
)
from app.services.extraction.parser import ParsedContent
from app.services.extraction.service import ExtractionResult

client = TestClient(app)


def _fake_result(url: str) -> ExtractionResult:
    return ExtractionResult(
        requested_url=url,
        final_url=url,
        status_code=200,
        content=ParsedContent(
            title="Example Title",
            author=None,
            description=None,
            site_name=None,
            published_date=None,
            main_text="Some meaningful extracted body text goes here.",
            word_count=8,
            character_count=48,
        ),
    )


def test_extraction_success(monkeypatch):
    monkeypatch.setattr(
        extraction_api, "extract_content", lambda url: _fake_result(url)
    )
    response = client.post("/extraction", json={"url": "https://example.com/article"})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Example Title"
    assert body["word_count"] == 8
    assert body["requested_url"] == "https://example.com/article"


def test_extraction_rejects_malformed_url():
    response = client.post("/extraction", json={"url": "not-a-url"})
    assert response.status_code == 422  # pydantic validation error


def test_extraction_rejects_non_http_scheme():
    response = client.post("/extraction", json={"url": "ftp://example.com/file"})
    assert response.status_code == 422  # HttpUrl already restricts scheme


def test_extraction_ssrf_blocked_maps_to_400(monkeypatch):
    def _raise(url):
        raise SSRFBlockedError("Host resolves to a disallowed network address.")

    monkeypatch.setattr(extraction_api, "extract_content", _raise)
    response = client.post("/extraction", json={"url": "https://internal.example.com/"})
    assert response.status_code == 400
    assert response.json()["error"] == "SSRFBlockedError"


def test_extraction_insufficient_content_maps_to_422(monkeypatch):
    def _raise(url):
        raise InsufficientContentError("Not enough content.")

    monkeypatch.setattr(extraction_api, "extract_content", _raise)
    response = client.post("/extraction", json={"url": "https://example.com/thin-page"})
    assert response.status_code == 422
    assert response.json()["error"] == "InsufficientContentError"
