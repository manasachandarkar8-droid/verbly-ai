from __future__ import annotations

import httpx
import pytest
import respx

from pydantic import SecretStr

from app.services.ai.cloudflare_client import (
    CLOUDFLARE_API_BASE,
    CLOUDFLARE_MODEL,
    CloudflareClient,
    CloudflareConfigurationError,
    CloudflareAuthenticationError,
    CloudflarePaidPlanRequiredError,
    CloudflareQuotaExceededError,
    CloudflareRateLimitError,
    CloudflareTimeoutError,
    CloudflareConnectionError,
    CloudflareServerError,
    CloudflareRequestError,
    CloudflareResponseError,
)


ACCOUNT_ID = "test-account-id"
API_TOKEN = SecretStr("test-token")

ENDPOINT = (
    f"{CLOUDFLARE_API_BASE}/"
    f"{ACCOUNT_ID}/ai/v1/chat/completions"
)

MESSAGES = [
    {
        "role": "system",
        "content": "Return JSON.",
    },
    {
        "role": "user",
        "content": "Analyze this text.",
    },
]

SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
        },
    },
    "required": ["summary"],
}


def create_client() -> CloudflareClient:
    return CloudflareClient(
        account_id=ACCOUNT_ID,
        api_token=API_TOKEN,
        timeout_seconds=5.0,
    )


def success_response() -> dict:
    return {
        "choices": [
            {
                "message": {
                    "content": '{"summary": "Test summary"}',
                },
            },
        ],
    }


def error_response(code: int) -> dict:
    return {
        "success": False,
        "errors": [
            {
                "code": code,
                "message": "Test error",
            },
        ],
    }


def test_successful_structured_completion():
    client = create_client()

    with respx.mock(assert_all_called=True) as router:
        route = router.post(ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json=success_response(),
            )
        )

        result = client.create_structured_completion(
            messages=MESSAGES,
            schema_name="content_analysis",
            json_schema=SCHEMA,
        )

    assert result == {
        "summary": "Test summary",
    }

    request = route.calls[0].request

    assert request.headers["Authorization"] == (
        "Bearer test-token"
    )

    import json

    payload = json.loads(request.content)

    assert payload["model"] == CLOUDFLARE_MODEL
    assert payload["stream"] is False

    assert "response_format" not in payload

    system_message = next(
        message
        for message in payload["messages"]
        if message["role"] == "system"
    )

    assert "content_analysis" in system_message["content"]
    assert "JSON Schema" in system_message["content"]
    assert '"summary"' in system_message["content"]
    



def test_missing_account_id():
    with pytest.raises(CloudflareConfigurationError):
        CloudflareClient(
            account_id="",
            api_token=API_TOKEN,
        )


def test_invalid_account_id():
    with pytest.raises(CloudflareConfigurationError):
        CloudflareClient(
            account_id="invalid/account",
            api_token=API_TOKEN,
        )


def test_missing_api_token():
    with pytest.raises(CloudflareConfigurationError):
        CloudflareClient(
            account_id=ACCOUNT_ID,
            api_token=SecretStr(""),
        )


def test_invalid_timeout():
    with pytest.raises(ValueError):
        CloudflareClient(
            account_id=ACCOUNT_ID,
            api_token=API_TOKEN,
            timeout_seconds=0,
        )


def test_authentication_error():
    client = create_client()

    with respx.mock:
        respx.post(ENDPOINT).mock(
            return_value=httpx.Response(401)
        )

        with pytest.raises(CloudflareAuthenticationError):
            client.create_structured_completion(
                messages=MESSAGES,
                schema_name="test",
                json_schema=SCHEMA,
            )


def test_paid_plan_required():
    client = create_client()

    with respx.mock:
        respx.post(ENDPOINT).mock(
            return_value=httpx.Response(
                403,
                json=error_response(5035),
            )
        )

        with pytest.raises(CloudflarePaidPlanRequiredError):
            client.create_structured_completion(
                messages=MESSAGES,
                schema_name="test",
                json_schema=SCHEMA,
            )


def test_daily_free_quota_exhausted():
    client = create_client()

    with respx.mock:
        respx.post(ENDPOINT).mock(
            return_value=httpx.Response(
                429,
                json=error_response(3036),
            )
        )

        with pytest.raises(CloudflareQuotaExceededError):
            client.create_structured_completion(
                messages=MESSAGES,
                schema_name="test",
                json_schema=SCHEMA,
            )


def test_temporary_capacity_error():
    client = create_client()

    with respx.mock:
        respx.post(ENDPOINT).mock(
            return_value=httpx.Response(
                429,
                json=error_response(3040),
            )
        )

        with pytest.raises(CloudflareRateLimitError):
            client.create_structured_completion(
                messages=MESSAGES,
                schema_name="test",
                json_schema=SCHEMA,
            )


def test_generic_forbidden_error():
    client = create_client()

    with respx.mock:
        respx.post(ENDPOINT).mock(
            return_value=httpx.Response(
                403,
                json=error_response(5018),
            )
        )

        with pytest.raises(CloudflareAuthenticationError):
            client.create_structured_completion(
                messages=MESSAGES,
                schema_name="test",
                json_schema=SCHEMA,
            )


def test_timeout_error():
    client = create_client()

    with respx.mock:
        respx.post(ENDPOINT).mock(
            side_effect=httpx.ReadTimeout("Timed out")
        )

        with pytest.raises(CloudflareTimeoutError):
            client.create_structured_completion(
                messages=MESSAGES,
                schema_name="test",
                json_schema=SCHEMA,
            )


def test_connection_error():
    client = create_client()

    with respx.mock:
        respx.post(ENDPOINT).mock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        with pytest.raises(CloudflareConnectionError):
            client.create_structured_completion(
                messages=MESSAGES,
                schema_name="test",
                json_schema=SCHEMA,
            )


def test_server_error():
    client = create_client()

    with respx.mock:
        respx.post(ENDPOINT).mock(
            return_value=httpx.Response(503)
        )

        with pytest.raises(CloudflareServerError):
            client.create_structured_completion(
                messages=MESSAGES,
                schema_name="test",
                json_schema=SCHEMA,
            )


def test_bad_request_error():
    client = create_client()

    with respx.mock:
        respx.post(ENDPOINT).mock(
            return_value=httpx.Response(400)
        )

        with pytest.raises(CloudflareRequestError):
            client.create_structured_completion(
                messages=MESSAGES,
                schema_name="test",
                json_schema=SCHEMA,
            )


def test_invalid_json_response():
    client = create_client()

    with respx.mock:
        respx.post(ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": "not valid JSON",
                            },
                        },
                    ],
                },
            )
        )

        with pytest.raises(CloudflareResponseError):
            client.create_structured_completion(
                messages=MESSAGES,
                schema_name="test",
                json_schema=SCHEMA,
            )


def test_missing_response_content():
    client = create_client()

    with respx.mock:
        respx.post(ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={"choices": []},
            )
        )

        with pytest.raises(CloudflareResponseError):
            client.create_structured_completion(
                messages=MESSAGES,
                schema_name="test",
                json_schema=SCHEMA,
            )


def test_empty_response_content():
    client = create_client()

    with respx.mock:
        respx.post(ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": " ",
                            },
                        },
                    ],
                },
            )
        )

        with pytest.raises(CloudflareResponseError):
            client.create_structured_completion(
                messages=MESSAGES,
                schema_name="test",
                json_schema=SCHEMA,
            )


def test_non_object_json_response():
    client = create_client()

    with respx.mock:
        respx.post(ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": '["not", "an", "object"]',
                            },
                        },
                    ],
                },
            )
        )

        with pytest.raises(CloudflareResponseError):
            client.create_structured_completion(
                messages=MESSAGES,
                schema_name="test",
                json_schema=SCHEMA,
            )


def test_empty_schema_name():
    client = create_client()

    with pytest.raises(ValueError):
        client.create_structured_completion(
            messages=MESSAGES,
            schema_name=" ",
            json_schema=SCHEMA,
        )

@pytest.mark.parametrize(
    "timeout_seconds",
    [0, -1, float("nan"), float("inf"), float("-inf")],
)
def test_invalid_request_timeout(timeout_seconds):
    client = create_client()

    with pytest.raises(ValueError):
        client.create_structured_completion(
            messages=MESSAGES,
            schema_name="test_schema",
            json_schema=SCHEMA,
            timeout_seconds=timeout_seconds,
        )

def test_request_timeout_override():
    client = create_client()

    with respx.mock(assert_all_called=True) as router:
        route = router.post(ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json=success_response(),
            )
        )

        client.create_structured_completion(
            messages=MESSAGES,
            schema_name="content_analysis",
            json_schema=SCHEMA,
            timeout_seconds=2.5,
        )

    timeout = route.calls[0].request.extensions["timeout"]
    assert timeout["read"] == pytest.approx(2.5)
