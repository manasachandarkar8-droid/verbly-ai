from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.grammar import router as grammar_router
from app.core.exceptions import register_exception_handlers
from app.schemas.grammar import MAX_TEXT_LENGTH


@pytest.fixture()
def app() -> FastAPI:
    application = FastAPI()
    application.include_router(grammar_router)
    register_exception_handlers(application)
    return application


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def _mock_check_text(monkeypatch, matches: list[dict], *, status_code: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"matches": matches})

    # Patch the transport-building seam used inside app.services.grammar.client
    # so the whole real pipeline (client -> mapper -> analysis -> service ->
    # api) runs, just without any real network call.
    import app.services.grammar.client as client_module

    original_build_client = client_module._build_client

    def fake_build_client(transport=None):
        return original_build_client(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(client_module, "_build_client", fake_build_client)


SAMPLE_MATCH = {
    "message": "Possible spelling mistake found.",
    "shortMessage": "Spelling mistake",
    "offset": 8,
    "length": 4,
    "replacements": [{"value": "test"}],
    "context": {"text": "This is a testt sentence.", "offset": 8, "length": 4},
    "rule": {
        "id": "MORFOLOGIK_RULE_EN_US",
        "issueType": "misspelling",
        "category": {"id": "TYPOS", "name": "Possible Typo"},
    },
}


def test_grammar_endpoint_success(client: TestClient, monkeypatch):
    _mock_check_text(monkeypatch, [SAMPLE_MATCH])

    response = client.post("/grammar", json={"text": "This is a testt sentence."})

    assert response.status_code == 200
    body = response.json()
    assert body["text_length"] == len("This is a testt sentence.")
    assert body["finding_count"] == 1
    assert len(body["findings"]) == 1
    finding = body["findings"][0]
    assert finding["message"] == "Possible spelling mistake found."
    assert finding["severity"] == "error"
    assert finding["offset"] == 8
    assert finding["length"] == 4
    assert finding["replacements"] == ["test"]
    assert body["issues"] == ["Possible spelling mistake found."]


def test_grammar_endpoint_clean_text_returns_no_findings(client: TestClient, monkeypatch):
    _mock_check_text(monkeypatch, [])

    response = client.post("/grammar", json={"text": "This is a clean sentence."})

    assert response.status_code == 200
    body = response.json()
    assert body["finding_count"] == 0
    assert body["findings"] == []
    assert body["issues"] == []


def test_grammar_endpoint_empty_text_returns_422(client: TestClient):
    response = client.post("/grammar", json={"text": ""})
    assert response.status_code == 422


def test_grammar_endpoint_whitespace_only_text_returns_422(client: TestClient):
    response = client.post("/grammar", json={"text": "   \n\t  "})
    assert response.status_code == 422


def test_grammar_endpoint_missing_text_field_returns_422(client: TestClient):
    response = client.post("/grammar", json={})
    assert response.status_code == 422


def test_grammar_endpoint_oversized_text_returns_422(client: TestClient):
    response = client.post("/grammar", json={"text": "a" * (MAX_TEXT_LENGTH + 1)})
    assert response.status_code == 422


def test_grammar_endpoint_max_length_text_is_accepted(client: TestClient, monkeypatch):
    _mock_check_text(monkeypatch, [])

    response = client.post("/grammar", json={"text": "a" * MAX_TEXT_LENGTH})

    assert response.status_code == 200


def test_grammar_endpoint_engine_timeout_returns_504(client: TestClient, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    import app.services.grammar.client as client_module

    original_build_client = client_module._build_client
    monkeypatch.setattr(
        client_module,
        "_build_client",
        lambda transport=None: original_build_client(transport=httpx.MockTransport(handler)),
    )

    response = client.post("/grammar", json={"text": "Some text."})

    assert response.status_code == 504
    assert response.json()["error"] == "GrammarEngineTimeoutError"


def test_grammar_endpoint_engine_unavailable_returns_502(client: TestClient, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    import app.services.grammar.client as client_module

    original_build_client = client_module._build_client
    monkeypatch.setattr(
        client_module,
        "_build_client",
        lambda transport=None: original_build_client(transport=httpx.MockTransport(handler)),
    )

    response = client.post("/grammar", json={"text": "Some text."})

    assert response.status_code == 502
    assert response.json()["error"] == "GrammarEngineUnavailableError"


def test_grammar_endpoint_engine_bad_response_returns_502(client: TestClient, monkeypatch):
    _mock_check_text(monkeypatch, [], status_code=500)

    response = client.post("/grammar", json={"text": "Some text."})

    assert response.status_code == 502
    assert response.json()["error"] == "GrammarEngineResponseError"


def test_grammar_endpoint_response_schema_shape(client: TestClient, monkeypatch):
    _mock_check_text(monkeypatch, [SAMPLE_MATCH])

    response = client.post("/grammar", json={"text": "This is a testt sentence."})

    body = response.json()
    assert set(body.keys()) == {"text_length", "finding_count", "findings", "issues"}
    finding = body["findings"][0]
    assert set(finding.keys()) == {
        "message",
        "short_message",
        "category",
        "rule_id",
        "issue_type",
        "severity",
        "offset",
        "length",
        "context",
        "replacements",
    }

