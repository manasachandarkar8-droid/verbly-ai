import json

import httpx
import pytest
import respx
from pydantic import SecretStr

from app.services.rewrite.groq_client import (
    GROQ_REWRITE_API_URL,
    GROQ_REWRITE_MODEL,
    GROQ_MAX_COMPLETION_TOKENS,
    RewriteGroqClient,
    RewriteGroqConfigurationError,
    RewriteGroqAuthenticationError,
    RewriteGroqRateLimitError,
    RewriteGroqTimeoutError,
    RewriteGroqConnectionError,
    RewriteGroqServerError,
    RewriteGroqRequestError,
    RewriteGroqResponseError,
)


@pytest.fixture
def client():
    return RewriteGroqClient(
        api_key=SecretStr("test-rewrite-api-key"),
        timeout_seconds=80.0,
        read_timeout_seconds=30.0,
    )


def test_missing_api_key():
    with pytest.raises(RewriteGroqConfigurationError):
        RewriteGroqClient(api_key=SecretStr(""))


@pytest.mark.parametrize(
    "timeout",
    [0, -1, float("nan"), float("inf"), float("-inf")],
)
def test_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        RewriteGroqClient(
            api_key=SecretStr("test-key"),
            timeout_seconds=timeout,
        )


@pytest.mark.parametrize(
    "timeout",
    [0, -1, float("nan"), float("inf"), float("-inf")],
)
def test_invalid_read_timeout(timeout):
    with pytest.raises(ValueError):
        RewriteGroqClient(
            api_key=SecretStr("test-key"),
            read_timeout_seconds=timeout,
        )


@respx.mock
def test_successful_rewrite(client):
    respx.post(GROQ_REWRITE_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": "Improved website content."
                        },
                    }
                ]
            },
        )
    )

    result = client.rewrite(
        messages=[
            {
                "role": "user",
                "content": "Rewrite this website content.",
            }
        ],
    )

    assert result == "Improved website content."


@respx.mock
def test_correct_model_authentication_and_payload(client):
    route = respx.post(GROQ_REWRITE_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": "Rewritten content."
                        },
                    }
                ]
            },
        )
    )

    client.rewrite(
        messages=[
            {
                "role": "user",
                "content": "Rewrite this content.",
            }
        ],
    )

    request = route.calls.last.request

    assert request.headers["Authorization"] == (
        "Bearer test-rewrite-api-key"
    )

    payload = json.loads(request.content)

    assert payload["model"] == GROQ_REWRITE_MODEL
    assert payload["stream"] is False
    assert payload["max_completion_tokens"] == (
        GROQ_MAX_COMPLETION_TOKENS
    )


@pytest.mark.parametrize("status_code", [401, 403])
@respx.mock
def test_authentication_error(client, status_code):
    respx.post(GROQ_REWRITE_API_URL).mock(
        return_value=httpx.Response(status_code)
    )

    with pytest.raises(RewriteGroqAuthenticationError):
        client.rewrite(
            messages=[
                {"role": "user", "content": "Test content"}
            ]
        )


@respx.mock
def test_rate_limit_error(client):
    respx.post(GROQ_REWRITE_API_URL).mock(
        return_value=httpx.Response(429)
    )

    with pytest.raises(RewriteGroqRateLimitError):
        client.rewrite(
            messages=[
                {"role": "user", "content": "Test content"}
            ]
        )


@respx.mock
def test_timeout_status_error(client):
    respx.post(GROQ_REWRITE_API_URL).mock(
        return_value=httpx.Response(408)
    )

    with pytest.raises(RewriteGroqTimeoutError):
        client.rewrite(
            messages=[
                {"role": "user", "content": "Test content"}
            ]
        )


@respx.mock
def test_server_error(client):
    respx.post(GROQ_REWRITE_API_URL).mock(
        return_value=httpx.Response(503)
    )

    with pytest.raises(RewriteGroqServerError):
        client.rewrite(
            messages=[
                {"role": "user", "content": "Test content"}
            ]
        )


@respx.mock
def test_bad_request_error(client):
    respx.post(GROQ_REWRITE_API_URL).mock(
        return_value=httpx.Response(400)
    )

    with pytest.raises(RewriteGroqRequestError):
        client.rewrite(
            messages=[
                {"role": "user", "content": "Test content"}
            ]
        )


@respx.mock
def test_connection_error(client):
    respx.post(GROQ_REWRITE_API_URL).mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

    with pytest.raises(RewriteGroqConnectionError):
        client.rewrite(
            messages=[
                {"role": "user", "content": "Test content"}
            ]
        )


@respx.mock
def test_read_timeout_error(client):
    respx.post(GROQ_REWRITE_API_URL).mock(
        side_effect=httpx.ReadTimeout("Request timed out")
    )

    with pytest.raises(RewriteGroqTimeoutError):
        client.rewrite(
            messages=[
                {"role": "user", "content": "Test content"}
            ]
        )


@respx.mock
def test_invalid_json_response(client):
    respx.post(GROQ_REWRITE_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={"unexpected": "response"},
        )
    )

    with pytest.raises(RewriteGroqResponseError):
        client.rewrite(
            messages=[
                {"role": "user", "content": "Test content"}
            ]
        )


@pytest.mark.parametrize(
    "content",
    ["", "   ", None, 123],
)
@respx.mock
def test_invalid_content_response(client, content):
    respx.post(GROQ_REWRITE_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": content},
                    }
                ]
            },
        )
    )

    with pytest.raises(RewriteGroqResponseError):
        client.rewrite(
            messages=[
                {"role": "user", "content": "Test content"}
            ]
        )


@respx.mock
def test_truncated_response_is_rejected(client):
    respx.post(GROQ_REWRITE_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {
                            "content": "Incomplete rewritten text."
                        },
                    }
                ]
            },
        )
    )

    with pytest.raises(RewriteGroqResponseError):
        client.rewrite(
            messages=[
                {"role": "user", "content": "Test content"}
            ]
        )


def test_empty_messages_rejected(client):
    with pytest.raises(ValueError):
        client.rewrite(messages=[])


@pytest.mark.parametrize(
    "message",
    [
        {"role": "invalid", "content": "Test"},
        {"role": "user", "content": ""},
        {"role": "user", "content": "   "},
        {"role": "user", "content": None},
        {"role": "user"},
    ],
)
def test_invalid_messages_rejected(client, message):
    with pytest.raises(ValueError):
        client.rewrite(messages=[message])


@respx.mock
def test_read_timeout_is_limited_to_30_seconds(client):
    route = respx.post(GROQ_REWRITE_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "Rewritten."},
                    }
                ]
            },
        )
    )

    client.rewrite(
        messages=[
            {"role": "user", "content": "Test content"}
        ]
    )

    timeout = route.calls.last.request.extensions["timeout"]

    assert timeout["read"] == pytest.approx(30.0)


@respx.mock
def test_timeout_override_respects_read_timeout(client):
    route = respx.post(GROQ_REWRITE_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "Rewritten."},
                    }
                ]
            },
        )
    )

    client.rewrite(
        messages=[
            {"role": "user", "content": "Test content"}
        ],
        timeout_seconds=20.0,
    )

    timeout = route.calls.last.request.extensions["timeout"]

    assert timeout["read"] == pytest.approx(20.0)


@pytest.mark.parametrize(
    "timeout",
    [0, -1, float("nan"), float("inf"), float("-inf")],
)
def test_invalid_request_timeout_rejected(client, timeout):
    with pytest.raises(ValueError):
        client.rewrite(
            messages=[
                {"role": "user", "content": "Test content"}
            ],
            timeout_seconds=timeout,
        )