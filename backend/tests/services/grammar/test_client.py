"""
Client tests. All network I/O is replaced with httpx.MockTransport --
no live LanguageTool server is required.
"""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.services.grammar.client import LanguageToolCheckResult, check_text
from app.services.grammar.exceptions import (
    GrammarEngineResponseError,
    GrammarEngineTimeoutError,
    GrammarEngineUnavailableError,
)


def _run(coro):
    return asyncio.run(coro)


SAMPLE_MATCH = {
    "message": "Possible spelling mistake found.",
    "shortMessage": "Spelling mistake",
    "offset": 5,
    "length": 4,
    "replacements": [{"value": "teh"}],
    "context": {"text": "This teh sentence.", "offset": 5, "length": 4},
    "rule": {
        "id": "MORFOLOGIK_RULE_EN_US",
        "issueType": "misspelling",
        "category": {"id": "TYPOS", "name": "Possible Typo"},
    },
}


def test_check_text_success_returns_matches():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/check"
        return httpx.Response(200, json={"matches": [SAMPLE_MATCH]})

    result = _run(check_text("This teh sentence.", _transport=httpx.MockTransport(handler)))

    assert isinstance(result, LanguageToolCheckResult)
    assert result.matches == [SAMPLE_MATCH]


def test_check_text_sends_expected_form_fields():
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(200, json={"matches": []})

    _run(check_text("Some text.", _transport=httpx.MockTransport(handler)))

    assert len(seen_requests) == 1
    sent = seen_requests[0]
    assert sent.method == "POST"
    assert sent.url.path == "/v2/check"
    body = sent.content.decode("utf-8")
    assert "text=Some+text." in body or "text=Some%20text." in body
    assert "language=en-US" in body


def test_check_text_empty_matches():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"matches": []})

    result = _run(check_text("Clean text.", _transport=httpx.MockTransport(handler)))
    assert result.matches == []


def test_check_text_timeout_raises_grammar_engine_timeout_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    with pytest.raises(GrammarEngineTimeoutError):
        _run(check_text("Some text.", _transport=httpx.MockTransport(handler)))


def test_check_text_connection_failure_raises_grammar_engine_unavailable_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(GrammarEngineUnavailableError):
        _run(check_text("Some text.", _transport=httpx.MockTransport(handler)))


def test_check_text_non_2xx_raises_grammar_engine_response_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "internal error"})

    with pytest.raises(GrammarEngineResponseError):
        _run(check_text("Some text.", _transport=httpx.MockTransport(handler)))


def test_check_text_client_error_status_raises_grammar_engine_response_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "bad request"})

    with pytest.raises(GrammarEngineResponseError):
        _run(check_text("Some text.", _transport=httpx.MockTransport(handler)))


def test_check_text_malformed_json_raises_grammar_engine_response_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json{{{", headers={"content-type": "application/json"})

    with pytest.raises(GrammarEngineResponseError):
        _run(check_text("Some text.", _transport=httpx.MockTransport(handler)))


def test_check_text_missing_matches_field_raises_grammar_engine_response_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"language": {"code": "en-US"}})

    with pytest.raises(GrammarEngineResponseError):
        _run(check_text("Some text.", _transport=httpx.MockTransport(handler)))


def test_check_text_matches_not_a_list_raises_grammar_engine_response_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"matches": "not-a-list"})

    with pytest.raises(GrammarEngineResponseError):
        _run(check_text("Some text.", _transport=httpx.MockTransport(handler)))


def test_check_text_response_not_a_json_object_raises_grammar_engine_response_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=json.dumps([1, 2, 3]).encode("utf-8"))

    with pytest.raises(GrammarEngineResponseError):
        _run(check_text("Some text.", _transport=httpx.MockTransport(handler)))

