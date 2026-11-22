from __future__ import annotations

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.rewrite import router as rewrite_router
from app.schemas.rewrite import MAX_REWRITE_CHARACTERS

from app.services.rewrite.admission import (
    RewriteCapacityExceededError,
)

from app.services.rewrite.cloudflare_client import (
    RewriteCloudflareQuotaExceededError,
    RewriteCloudflareAuthenticationError,
    RewriteCloudflarePaidPlanRequiredError,
)

from app.services.rewrite.provider import (
    RewriteDeadlineExceededError,
    RewriteProvidersUnavailableError,
)
from app.services.rewrite.groq_client import (
    RewriteGroqAuthenticationError,
)
from app.api.rewrite_body_limit import (
    MAX_REWRITE_REQUEST_BODY_BYTES,
    RewriteBodyLimitMiddleware,
)

@pytest.fixture()
def app() -> FastAPI:
    application = FastAPI()

    application.add_middleware(RewriteBodyLimitMiddleware)
    application.include_router(rewrite_router)

    @application.post("/other")
    async def other_endpoint():
        return {"status": "ok"}

    return application


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def rewrite_service():
    return Mock()


def _mock_rewrite_service(monkeypatch, service):
    monkeypatch.setattr(
        "app.api.rewrite.get_rewrite_service",
        lambda: service,
    )


def test_rewrite_endpoint_success(
    client,
    rewrite_service,
    monkeypatch,
):
    rewrite_service.rewrite.return_value = "Improved content."

    _mock_rewrite_service(monkeypatch, rewrite_service)

    response = client.post(
        "/rewrite",
        json={"main_text": "Original content."},
    )

    assert response.status_code == 200
    assert response.json() == {
        "rewritten_text": "Improved content."
    }

    rewrite_service.rewrite.assert_called_once_with(
    	main_text="Original content.",
    	tone="concise",
    	custom_instruction=None,
    )


def test_rewrite_endpoint_empty_content_returns_422(client):
    response = client.post(
        "/rewrite",
        json={"main_text": ""},
    )

    assert response.status_code == 422


def test_rewrite_endpoint_missing_content_returns_422(client):
    response = client.post(
        "/rewrite",
        json={},
    )

    assert response.status_code == 422


def test_rewrite_endpoint_whitespace_only_content_returns_422(client):
    response = client.post(
        "/rewrite",
        json={"main_text": "     \n\t   "},
    )

    assert response.status_code == 422

def test_rewrite_capacity_exceeded_returns_503(
    client,
    rewrite_service,
    monkeypatch,
):
    rewrite_service.rewrite.side_effect = (
        RewriteCapacityExceededError()
    )

    _mock_rewrite_service(monkeypatch, rewrite_service)

    response = client.post(
        "/rewrite",
        json={"main_text": "Original content."},
    )

    assert response.status_code == 503


def test_rewrite_provider_unavailable_returns_503(
    client,
    rewrite_service,
    monkeypatch,
):
    rewrite_service.rewrite.side_effect = (
        RewriteProvidersUnavailableError()
    )

    _mock_rewrite_service(monkeypatch, rewrite_service)

    response = client.post(
        "/rewrite",
        json={"main_text": "Original content."},
    )

    assert response.status_code == 503


def test_rewrite_deadline_exceeded_returns_504(
    client,
    rewrite_service,
    monkeypatch,
):
    rewrite_service.rewrite.side_effect = (
        RewriteDeadlineExceededError()
    )

    _mock_rewrite_service(monkeypatch, rewrite_service)

    response = client.post(
        "/rewrite",
        json={"main_text": "Original content."},
    )

    assert response.status_code == 504


def test_cloudflare_free_quota_exhausted_returns_503(
    client,
    rewrite_service,
    monkeypatch,
):
    rewrite_service.rewrite.side_effect = (
        RewriteCloudflareQuotaExceededError()
    )

    _mock_rewrite_service(monkeypatch, rewrite_service)

    response = client.post(
        "/rewrite",
        json={"main_text": "Original content."},
    )

    assert response.status_code == 503
    assert "Paid usage is disabled" in response.json()["detail"]
    


def test_provider_authentication_error_does_not_expose_details(
    client,
    rewrite_service,
    monkeypatch,
):
    rewrite_service.rewrite.side_effect = (
        RewriteCloudflareAuthenticationError(
            "Sensitive authentication details"
        )
    )

    _mock_rewrite_service(monkeypatch, rewrite_service)

    response = client.post(
        "/rewrite",
        json={"main_text": "Original content."},
    )

    assert response.status_code == 503
    assert "Sensitive authentication details" not in response.text

def test_cloudflare_paid_plan_required_returns_503(
    client,
    rewrite_service,
    monkeypatch,
):
    rewrite_service.rewrite.side_effect = (
        RewriteCloudflarePaidPlanRequiredError(
            "Sensitive paid-plan details"
        )
    )

    _mock_rewrite_service(monkeypatch, rewrite_service)

    response = client.post(
        "/rewrite",
        json={"main_text": "Original content."},
    )

    assert response.status_code == 503
    assert "Paid usage is disabled" in response.json()["detail"]
    assert "Sensitive paid-plan details" not in response.text    

def test_groq_authentication_error_does_not_expose_details(
    client,
    rewrite_service,
    monkeypatch,
):
    rewrite_service.rewrite.side_effect = (
        RewriteGroqAuthenticationError(
            "Sensitive Groq API credentials"
        )
    )

    _mock_rewrite_service(monkeypatch, rewrite_service)

    response = client.post(
        "/rewrite",
        json={"main_text": "Original content."},
    )

    assert response.status_code == 503
    assert "Sensitive Groq API credentials" not in response.text    

def test_unexpected_internal_error_does_not_expose_details(
    app,
    rewrite_service,
    monkeypatch,
):
    rewrite_service.rewrite.side_effect = RuntimeError(
        "Sensitive internal implementation details"
    )

    _mock_rewrite_service(monkeypatch, rewrite_service)

    with TestClient(
        app,
        raise_server_exceptions=False,
    ) as safe_client:
        response = safe_client.post(
            "/rewrite",
            json={"main_text": "Original content."},
        )

    assert response.status_code == 500
    assert "Sensitive internal implementation details" not in response.text    

def test_rewrite_rejects_request_body_over_3_mib(client):
    oversized_body = b"x" * (
        MAX_REWRITE_REQUEST_BODY_BYTES + 1
    )

    response = client.post(
        "/rewrite",
        content=oversized_body,
    )

    assert response.status_code == 413
    assert "3 MiB limit" in response.json()["detail"]


def test_body_limit_does_not_affect_other_endpoints(client):
    oversized_body = b"x" * (
        MAX_REWRITE_REQUEST_BODY_BYTES + 1
    )

    response = client.post(
        "/other",
        content=oversized_body,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}    

def test_rewrite_rejects_oversized_streamed_body(client):
    chunk_size = 1024 * 1024

    streamed_body = (
        chunk
        for chunk in [
            b"x" * chunk_size,
            b"x" * chunk_size,
            b"x" * chunk_size,
            b"x",
        ]
    )

    response = client.post(
        "/rewrite",
        content=streamed_body,
    )

    assert response.status_code == 413
    assert "3 MiB limit" in response.json()["detail"]    

def test_rewrite_rejects_malformed_content_length(client):
    response = client.post(
        "/rewrite",
        content=b'{"main_text":"hello"}',
        headers={"Content-Length": "invalid"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Content-Length header."


def test_rewrite_rejects_duplicate_content_length(client):
    response = client.post(
        "/rewrite",
        content=b'{"main_text":"hello"}',
        headers=[
            ("Content-Length", "21"),
            ("Content-Length", "21"),
        ],
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Multiple Content-Length headers are not allowed."
    )    


@pytest.mark.parametrize(
    "tone",
    [
        "professional",
        "friendly",
        "seo-optimized",
    ],
)
def test_rewrite_endpoint_forwards_selected_tone(
    client,
    rewrite_service,
    monkeypatch,
    tone,
):
    rewrite_service.rewrite.return_value = "Improved content."

    _mock_rewrite_service(monkeypatch, rewrite_service)

    response = client.post(
        "/rewrite",
        json={
            "main_text": "Original content.",
            "tone": tone,
        },
    )

    assert response.status_code == 200

    rewrite_service.rewrite.assert_called_once_with(
        main_text="Original content.",
        tone=tone,
        custom_instruction=None,
    )


def test_rewrite_endpoint_forwards_custom_instruction(
    client,
    rewrite_service,
    monkeypatch,
):
    rewrite_service.rewrite.return_value = "Improved content."

    _mock_rewrite_service(monkeypatch, rewrite_service)

    response = client.post(
        "/rewrite",
        json={
            "main_text": "Original content.",
            "tone": "friendly",
            "custom_instruction": "Use simple sentences.",
        },
    )

    assert response.status_code == 200

    rewrite_service.rewrite.assert_called_once_with(
        main_text="Original content.",
        tone="friendly",
        custom_instruction="Use simple sentences.",
    )


def test_rewrite_endpoint_normalizes_custom_instruction(
    client,
    rewrite_service,
    monkeypatch,
):
    rewrite_service.rewrite.return_value = "Improved content."

    _mock_rewrite_service(monkeypatch, rewrite_service)

    response = client.post(
        "/rewrite",
        json={
            "main_text": "Original content.",
            "custom_instruction": "  Keep it simple  ",
        },
    )

    assert response.status_code == 200

    rewrite_service.rewrite.assert_called_once_with(
        main_text="Original content.",
        tone="concise",
        custom_instruction="Keep it simple",
    )


def test_rewrite_endpoint_rejects_invalid_tone(client):
    response = client.post(
        "/rewrite",
        json={
            "main_text": "Original content.",
            "tone": "aggressive",
        },
    )

    assert response.status_code == 422


def test_rewrite_endpoint_rejects_oversized_custom_instruction(client):
    response = client.post(
        "/rewrite",
        json={
            "main_text": "Original content.",
            "custom_instruction": "x" * 2001,
        },
    )

    assert response.status_code == 422


def test_rewrite_endpoint_accepts_maximum_custom_instruction(
    client,
    rewrite_service,
    monkeypatch,
):
    rewrite_service.rewrite.return_value = "Improved content."

    _mock_rewrite_service(monkeypatch, rewrite_service)

    instruction = "x" * 2000

    response = client.post(
        "/rewrite",
        json={
            "main_text": "Original content.",
            "custom_instruction": instruction,
        },
    )

    assert response.status_code == 200

    rewrite_service.rewrite.assert_called_once_with(
        main_text="Original content.",
        tone="concise",
        custom_instruction=instruction,
    )


def test_rewrite_endpoint_treats_whitespace_instruction_as_absent(
    client,
    rewrite_service,
    monkeypatch,
):
    rewrite_service.rewrite.return_value = "Improved content."

    _mock_rewrite_service(monkeypatch, rewrite_service)

    response = client.post(
        "/rewrite",
        json={
            "main_text": "Original content.",
            "custom_instruction": "   \n\t  ",
        },
    )

    assert response.status_code == 200

    rewrite_service.rewrite.assert_called_once_with(
        main_text="Original content.",
        tone="concise",
        custom_instruction=None,
    )