import httpx
import pytest
import respx
from pydantic import SecretStr

from app.services.ai.groq_client import (
    GROQ_API_URL,
    GROQ_MODEL,
    GroqAuthenticationError,
    GroqClient,
    GroqConfigurationError,
    GroqRateLimitError,
    GroqResponseError,
    GroqServerError,
)

from app.services.ai.groq_client import (
    GroqConnectionError,
    GroqRequestError,
    GroqTimeoutError,
)


@pytest.fixture
def client():
    return GroqClient(
        api_key=SecretStr("test-api-key"),
        timeout_seconds=5.0,
    )


def test_missing_api_key():
    with pytest.raises(GroqConfigurationError):
        GroqClient(api_key=SecretStr(""))


@respx.mock
def test_successful_structured_completion(client):
    respx.post(GROQ_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"summary": ["AI improves healthcare"]}'
                        }
                    }
                ]
            },
        )
    )

    result = client.create_structured_completion(
        messages=[{"role": "user", "content": "Analyze this text"}],
        schema_name="test_schema",
        json_schema={"type": "object"},
    )

    assert result == {
        "summary": ["AI improves healthcare"]
    }


@respx.mock
def test_correct_model_and_authentication(client):
    route = respx.post(GROQ_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"ok": true}'}}
                ]
            },
        )
    )

    client.create_structured_completion(
        messages=[{"role": "user", "content": "Test"}],
        schema_name="test_schema",
        json_schema={"type": "object"},
    )

    assert route.calls.last.request.headers["Authorization"] == (
        "Bearer test-api-key"
    )

    assert route.calls.last.request.content
    assert GROQ_MODEL in route.calls.last.request.content.decode()


@respx.mock
def test_rate_limit_error(client):
    respx.post(GROQ_API_URL).mock(
        return_value=httpx.Response(429)
    )

    with pytest.raises(GroqRateLimitError):
        client.create_structured_completion(
            messages=[{"role": "user", "content": "Test"}],
            schema_name="test_schema",
            json_schema={"type": "object"},
        )


@pytest.mark.parametrize("status_code", [401, 403])
@respx.mock
def test_authentication_error(client, status_code):
    respx.post(GROQ_API_URL).mock(
        return_value=httpx.Response(status_code)
    )

    with pytest.raises(GroqAuthenticationError):
        client.create_structured_completion(
            messages=[{"role": "user", "content": "Test"}],
            schema_name="test_schema",
            json_schema={"type": "object"},
        )


@respx.mock
def test_server_error(client):
    respx.post(GROQ_API_URL).mock(
        return_value=httpx.Response(503)
    )

    with pytest.raises(GroqServerError):
        client.create_structured_completion(
            messages=[{"role": "user", "content": "Test"}],
            schema_name="test_schema",
            json_schema={"type": "object"},
        )


@respx.mock
def test_invalid_json_response(client):
    respx.post(GROQ_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "not valid json"}}
                ]
            },
        )
    )

    with pytest.raises(GroqResponseError):
        client.create_structured_completion(
            messages=[{"role": "user", "content": "Test"}],
            schema_name="test_schema",
            json_schema={"type": "object"},
        )

@respx.mock
def test_connection_error(client):
    respx.post(GROQ_API_URL).mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

    with pytest.raises(GroqConnectionError):
        client.create_structured_completion(
            messages=[{"role": "user", "content": "Test"}],
            schema_name="test_schema",
            json_schema={"type": "object"},
        )


@respx.mock
def test_timeout_error(client):
    respx.post(GROQ_API_URL).mock(
        side_effect=httpx.ReadTimeout("Request timed out")
    )

    with pytest.raises(GroqTimeoutError):
        client.create_structured_completion(
            messages=[{"role": "user", "content": "Test"}],
            schema_name="test_schema",
            json_schema={"type": "object"},
        )


@respx.mock
def test_bad_request_error(client):
    respx.post(GROQ_API_URL).mock(
        return_value=httpx.Response(400)
    )

    with pytest.raises(GroqRequestError):
        client.create_structured_completion(
            messages=[{"role": "user", "content": "Test"}],
            schema_name="test_schema",
            json_schema={"type": "object"},
        )


@respx.mock
def test_unexpected_response_structure(client):
    respx.post(GROQ_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={"unexpected": "response"},
        )
    )

    with pytest.raises(GroqResponseError):
        client.create_structured_completion(
            messages=[{"role": "user", "content": "Test"}],
            schema_name="test_schema",
            json_schema={"type": "object"},
        )        

@respx.mock
def test_request_timeout_override(client):
    route = respx.post(GROQ_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"ok": true}'}}
                ]
            },
        )
    )

    client.create_structured_completion(
        messages=[{"role": "user", "content": "Test"}],
        schema_name="test_schema",
        json_schema={"type": "object"},
        timeout_seconds=2.5,
    )

    timeout = route.calls.last.request.extensions["timeout"]
    assert timeout["read"] == pytest.approx(2.5)
@pytest.mark.parametrize(
    "timeout_seconds",
    [0, -1, float("nan"), float("inf"), float("-inf")],
)
def test_invalid_request_timeout(client, timeout_seconds):
    with pytest.raises(ValueError):
        client.create_structured_completion(
            messages=[{"role": "user", "content": "Test"}],
            schema_name="test_schema",
            json_schema={"type": "object"},
            timeout_seconds=timeout_seconds,
        )