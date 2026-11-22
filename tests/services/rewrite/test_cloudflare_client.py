import httpx
import pytest
import respx
from pydantic import SecretStr

from app.services.rewrite.cloudflare_client import (
    CLOUDFLARE_REWRITE_MODEL,
    RewriteCloudflareClient,
    RewriteCloudflareAuthenticationError,
    RewriteCloudflarePaidPlanRequiredError,
    RewriteCloudflareQuotaExceededError,
    RewriteCloudflareRateLimitError,
    RewriteCloudflareTimeoutError,
    RewriteCloudflareConnectionError,
    RewriteCloudflareServerError,
    RewriteCloudflareRequestError,
    RewriteCloudflareResponseError,
    RewriteCloudflareConfigurationError,
)


ACCOUNT_ID = "a" * 32
API_TOKEN = "test-cloudflare-token"

ENDPOINT = (
    "https://api.cloudflare.com/client/v4/accounts/"
    f"{ACCOUNT_ID}/ai/run/{CLOUDFLARE_REWRITE_MODEL}"
)


@pytest.fixture
def client():
    return RewriteCloudflareClient(
        account_id=ACCOUNT_ID,
        api_token=SecretStr(API_TOKEN),
        timeout_seconds=80,
    )


@pytest.fixture
def messages():
    return [
        {
            "role": "system",
            "content": "Rewrite the content clearly.",
        },
        {
            "role": "user",
            "content": "This is an example paragraph.",
        },
    ]


def success_response(text="This is the rewritten paragraph."):
    return {
        "success": True,
        "errors": [],
        "messages": [],
        "result": {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": text,
                    }
                }
            ],
            "created": 1730000000,
            "id": "test-completion-id",
            "model": "@cf/google/gemma-4-26b-a4b-it",
            "object": "chat.completion",
            "usage": {},
        },
    }


def error_response(code):
    return {
        "success": False,
        "errors": [
            {
                "code": code,
                "message": "Test error",
            }
        ],
        "messages": [],
        "result": None,
    }


# --------------------------------------------------
# Successful requests
# --------------------------------------------------

@respx.mock
def test_successful_rewrite(client, messages):
    route = respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json=success_response(),
        )
    )

    result = client.rewrite(messages=messages)

    assert result == "This is the rewritten paragraph."
    assert route.called


@respx.mock
def test_request_uses_correct_endpoint(client, messages):
    route = respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json=success_response(),
        )
    )

    client.rewrite(messages=messages)

    assert route.called


@respx.mock
def test_request_contains_authorization_header(client, messages):
    route = respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json=success_response(),
        )
    )

    client.rewrite(messages=messages)

    request = route.calls.last.request

    assert request.headers["Authorization"] == (
        f"Bearer {API_TOKEN}"
    )


@respx.mock
def test_request_uses_approved_model_endpoint(client, messages):
    route = respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json=success_response(),
        )
    )

    client.rewrite(messages=messages)

    assert route.calls.last.request.url.path.endswith(
        CLOUDFLARE_REWRITE_MODEL
    )


@respx.mock
def test_request_sends_messages(client, messages):
    route = respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json=success_response(),
        )
    )

    client.rewrite(messages=messages)

    payload = route.calls.last.request.content
    import json

    body = json.loads(payload)

    assert body["messages"] == messages
    assert body["stream"] is False
    assert body["max_tokens"] == 4096


@respx.mock
def test_generated_text_is_stripped(client, messages):
    route = respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json=success_response("  Rewritten text.  "),
        )
    )

    result = client.rewrite(messages=messages)

    assert result == "Rewritten text."


# --------------------------------------------------
# Configuration validation
# --------------------------------------------------

def test_missing_account_id():
    with pytest.raises(RewriteCloudflareConfigurationError):
        RewriteCloudflareClient(
            account_id="",
            api_token=SecretStr(API_TOKEN),
        )


def test_invalid_account_id():
    with pytest.raises(RewriteCloudflareConfigurationError):
        RewriteCloudflareClient(
            account_id="invalid/account",
            api_token=SecretStr(API_TOKEN),
        )


def test_missing_api_token():
    with pytest.raises(RewriteCloudflareConfigurationError):
        RewriteCloudflareClient(
            account_id=ACCOUNT_ID,
            api_token=SecretStr(""),
        )


def test_invalid_api_token_type():
    with pytest.raises(RewriteCloudflareConfigurationError):
        RewriteCloudflareClient(
            account_id=ACCOUNT_ID,
            api_token="plain-text-token",
        )


def test_invalid_timeout():
    with pytest.raises(RewriteCloudflareConfigurationError):
        RewriteCloudflareClient(
            account_id=ACCOUNT_ID,
            api_token=SecretStr(API_TOKEN),
            timeout_seconds=0,
        )


# --------------------------------------------------
# Message validation
# --------------------------------------------------

def test_empty_messages(client):
    with pytest.raises(RewriteCloudflareRequestError):
        client.rewrite(messages=[])


def test_invalid_message_role(client):
    with pytest.raises(RewriteCloudflareRequestError):
        client.rewrite(
            messages=[
                {
                    "role": "invalid",
                    "content": "Test",
                }
            ]
        )


def test_empty_message_content(client):
    with pytest.raises(RewriteCloudflareRequestError):
        client.rewrite(
            messages=[
                {
                    "role": "user",
                    "content": " ",
                }
            ]
        )


def test_non_mapping_message(client):
    with pytest.raises(RewriteCloudflareRequestError):
        client.rewrite(messages=["invalid"])


def test_invalid_timeout_override(client, messages):
    with pytest.raises(RewriteCloudflareRequestError):
        client.rewrite(
            messages=messages,
            timeout_seconds=0,
        )


# --------------------------------------------------
# Authentication and free-plan protection
# --------------------------------------------------

@pytest.mark.parametrize("status_code", [401, 403])
@respx.mock
def test_authentication_error(client, messages, status_code):
    respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            status_code,
            json={"success": False, "errors": []},
        )
    )

    with pytest.raises(RewriteCloudflareAuthenticationError):
        client.rewrite(messages=messages)


@respx.mock
def test_paid_plan_required_error(client, messages):
    respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            403,
            json=error_response(5035),
        )
    )

    with pytest.raises(RewriteCloudflarePaidPlanRequiredError):
        client.rewrite(messages=messages)


@respx.mock
def test_daily_free_quota_exceeded(client, messages):
    respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            429,
            json=error_response(3036),
        )
    )

    with pytest.raises(RewriteCloudflareQuotaExceededError):
        client.rewrite(messages=messages)


@respx.mock
def test_rate_limit_error(client, messages):
    respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            429,
            json=error_response(3040),
        )
    )

    with pytest.raises(RewriteCloudflareRateLimitError):
        client.rewrite(messages=messages)


# --------------------------------------------------
# Network and server errors
# --------------------------------------------------

@respx.mock
def test_timeout_error(client, messages):
    respx.post(ENDPOINT).mock(
        side_effect=httpx.ReadTimeout("Timed out"),
    )

    with pytest.raises(RewriteCloudflareTimeoutError):
        client.rewrite(messages=messages)


@respx.mock
def test_connection_error(client, messages):
    respx.post(ENDPOINT).mock(
        side_effect=httpx.ConnectError("Connection failed"),
    )

    with pytest.raises(RewriteCloudflareConnectionError):
        client.rewrite(messages=messages)


@respx.mock
def test_server_error(client, messages):
    respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            500,
            json={"success": False},
        )
    )

    with pytest.raises(RewriteCloudflareServerError):
        client.rewrite(messages=messages)


@respx.mock
def test_request_timeout_status(client, messages):
    respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            408,
            json={"success": False},
        )
    )

    with pytest.raises(RewriteCloudflareTimeoutError):
        client.rewrite(messages=messages)


# --------------------------------------------------
# Response validation
# --------------------------------------------------

@respx.mock
def test_invalid_json_response(client, messages):
    respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            text="not-json",
        )
    )

    with pytest.raises(RewriteCloudflareResponseError):
        client.rewrite(messages=messages)


@respx.mock
def test_missing_result_object(client, messages):
    respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={
                "success": True,
                "result": None,
            },
        )
    )

    with pytest.raises(RewriteCloudflareResponseError):
        client.rewrite(messages=messages)


@respx.mock
def test_empty_generated_response(client, messages):
    respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json=success_response(" "),
        )
    )

    with pytest.raises(RewriteCloudflareResponseError):
        client.rewrite(messages=messages)


@respx.mock
def test_unsuccessful_cloudflare_response(client, messages):
    respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={
                "success": False,
                "errors": [],
            },
        )
    )

    with pytest.raises(RewriteCloudflareRequestError):
        client.rewrite(messages=messages)

# --------------------------------------------------
# Additional defensive validation tests
# --------------------------------------------------


@pytest.mark.parametrize(
    "account_id",
    [
        "a" * 31,                  # Too short
        "a" * 33,                  # Too long
        "g" * 32,                  # Non-hexadecimal character
        "a" * 31 + "!",            # Special character
    ],
)
def test_invalid_account_id_format(account_id):
    with pytest.raises(RewriteCloudflareConfigurationError):
        RewriteCloudflareClient(
            account_id=account_id,
            api_token=SecretStr(API_TOKEN),
        )


@pytest.mark.parametrize(
    "role",
    [
        [],
        {},
        123,
        None,
    ],
)
def test_non_string_message_role(client, role):
    with pytest.raises(RewriteCloudflareRequestError):
        client.rewrite(
            messages=[
                {
                    "role": role,
                    "content": "Test content.",
                }
            ]
        )


@respx.mock
def test_missing_success_field_in_response(client, messages):
    respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={
                "result": {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "Rewritten text.",
                            }
                        }
                    ]
                }
            },
        )
    )

    with pytest.raises(RewriteCloudflareResponseError):
        client.rewrite(messages=messages)