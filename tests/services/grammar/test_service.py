from __future__ import annotations

import asyncio

import httpx
import pytest

from app.services.grammar.exceptions import (
    GrammarEngineResponseError,
    GrammarEngineTimeoutError,
    GrammarEngineUnavailableError,
)
from app.services.grammar.service import GrammarAnalysisResult, analyze_grammar


def _run(coro):
    return asyncio.run(coro)


def _transport_returning(matches: list[dict], *, status_code: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"matches": matches})

    return httpx.MockTransport(handler)


def test_analyze_grammar_clean_text_returns_no_findings():
    result = _run(
        analyze_grammar("This is a clean sentence.", _transport=_transport_returning([]))
    )

    assert isinstance(result, GrammarAnalysisResult)
    assert result.findings == []
    assert result.text_length == len("This is a clean sentence.")


def test_analyze_grammar_returns_mapped_findings():
    matches = [
        {
            "message": "Possible spelling mistake found.",
            "offset": 8,
            "length": 4,
            "rule": {"id": "MORFOLOGIK_RULE_EN_US", "issueType": "misspelling"},
        }
    ]

    result = _run(analyze_grammar("This is a testt sentence.", _transport=_transport_returning(matches)))

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.message == "Possible spelling mistake found."
    assert finding.severity == "error"
    assert finding.offset == 8
    assert finding.length == 4


def test_analyze_grammar_output_is_deterministically_ordered():
    matches = [
        {"message": "Second.", "offset": 10, "length": 2, "rule": {"id": "R2"}},
        {"message": "First.", "offset": 0, "length": 2, "rule": {"id": "R1"}},
    ]

    result = _run(analyze_grammar("Some text here for testing.", _transport=_transport_returning(matches)))

    assert [f.message for f in result.findings] == ["First.", "Second."]


def test_analyze_grammar_deduplicates_identical_matches():
    match = {"message": "Dup.", "offset": 0, "length": 3, "rule": {"id": "R1"}}
    result = _run(analyze_grammar("Abc def.", _transport=_transport_returning([match, dict(match)])))

    assert len(result.findings) == 1


def test_analyze_grammar_text_length_reflects_submitted_text():
    text = "A" * 123
    result = _run(analyze_grammar(text, _transport=_transport_returning([])))

    assert result.text_length == 123


def test_analyze_grammar_propagates_timeout_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    with pytest.raises(GrammarEngineTimeoutError):
        _run(analyze_grammar("Some text.", _transport=httpx.MockTransport(handler)))


def test_analyze_grammar_propagates_unavailable_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(GrammarEngineUnavailableError):
        _run(analyze_grammar("Some text.", _transport=httpx.MockTransport(handler)))


def test_analyze_grammar_propagates_response_error():
    with pytest.raises(GrammarEngineResponseError):
        _run(analyze_grammar("Some text.", _transport=_transport_returning([], status_code=500)))


def test_analyze_grammar_is_deterministic_across_calls():
    matches = [
        {"message": "B.", "offset": 5, "length": 1, "rule": {"id": "RB"}},
        {"message": "A.", "offset": 0, "length": 1, "rule": {"id": "RA"}},
    ]

    result_1 = _run(analyze_grammar("Some text.", _transport=_transport_returning(matches)))
    result_2 = _run(analyze_grammar("Some text.", _transport=_transport_returning(matches)))

    assert [f.message for f in result_1.findings] == [f.message for f in result_2.findings]

