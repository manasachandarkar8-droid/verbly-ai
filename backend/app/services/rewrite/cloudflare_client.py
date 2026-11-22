from __future__ import annotations

import math
import re
from typing import Mapping, Sequence

import httpx
from pydantic import SecretStr


CLOUDFLARE_REWRITE_API_BASE = (
    "https://api.cloudflare.com/client/v4/accounts"
)
CLOUDFLARE_REWRITE_MODEL = "@cf/google/gemma-4-26b-a4b-it"
CLOUDFLARE_MAX_TOKENS = 4096


class RewriteCloudflareError(Exception):
    """Base exception for Feature 6 Cloudflare errors."""


class RewriteCloudflareConfigurationError(RewriteCloudflareError):
    pass


class RewriteCloudflareAuthenticationError(RewriteCloudflareError):
    pass


class RewriteCloudflarePaidPlanRequiredError(RewriteCloudflareError):
    pass


class RewriteCloudflareQuotaExceededError(RewriteCloudflareError):
    pass


class RewriteCloudflareRateLimitError(RewriteCloudflareError):
    pass


class RewriteCloudflareTimeoutError(RewriteCloudflareError):
    pass


class RewriteCloudflareConnectionError(RewriteCloudflareError):
    pass


class RewriteCloudflareServerError(RewriteCloudflareError):
    pass


class RewriteCloudflareRequestError(RewriteCloudflareError):
    pass


class RewriteCloudflareResponseError(RewriteCloudflareError):
    pass


class RewriteCloudflareClient:
    def __init__(
        self,
        *,
        account_id: str,
        api_token: SecretStr,
        timeout_seconds: float = 80.0,
    ) -> None:
        if not isinstance(account_id, str) or not account_id.strip():
            raise RewriteCloudflareConfigurationError(
                "Cloudflare account ID is required."
            )

        if not re.fullmatch(r"[0-9a-fA-F]{32}", account_id):
            raise RewriteCloudflareConfigurationError(
            "Cloudflare account ID has an invalid format."
            )

        if not isinstance(api_token, SecretStr):
            raise RewriteCloudflareConfigurationError(
                "Cloudflare API token must be provided as SecretStr."
            )

        if not api_token.get_secret_value().strip():
            raise RewriteCloudflareConfigurationError(
                "Cloudflare API token cannot be empty."
            )

        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise RewriteCloudflareConfigurationError(
                "Timeout must be a finite positive number."
            )

        self._account_id = account_id
        self._api_token = api_token
        self._timeout_seconds = float(timeout_seconds)

        self._endpoint = (
            f"{CLOUDFLARE_REWRITE_API_BASE}/"
            f"{account_id}/ai/run/{CLOUDFLARE_REWRITE_MODEL}"
        )

    @staticmethod
    def _validate_messages(
        messages: Sequence[Mapping[str, str]],
    ) -> list[dict[str, str]]:
        if (
            isinstance(messages, (str, bytes))
            or not isinstance(messages, Sequence)
            or not messages
        ):
            raise RewriteCloudflareRequestError(
                "At least one message is required."
            )

        validated: list[dict[str, str]] = []

        for message in messages:
            if not isinstance(message, Mapping):
                raise RewriteCloudflareRequestError(
                    "Each message must be a mapping."
                )

            role = message.get("role")
            content = message.get("content")

            if (
                not isinstance(role, str)
                or role not in {"system", "user", "assistant"}
            ):
                raise RewriteCloudflareRequestError(
                    "Message contains an unsupported role."
                )

            if not isinstance(content, str) or not content.strip():
                raise RewriteCloudflareRequestError(
                    "Message content cannot be empty."
                )

            validated.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        return validated
            

    @staticmethod
    def _extract_error_code(body: object) -> int | None:
        if not isinstance(body, dict):
            return None

        errors = body.get("errors")

        if not isinstance(errors, list):
            return None

        for error in errors:
            if isinstance(error, dict):
                code = error.get("code")

                if isinstance(code, int) and not isinstance(code, bool):
                    return code

        return None

    def rewrite(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        timeout_seconds: float | None = None,
    ) -> str:
        validated_messages = self._validate_messages(messages)

        effective_timeout = self._timeout_seconds

        if timeout_seconds is not None:
            if (
                isinstance(timeout_seconds, bool)
                or not isinstance(timeout_seconds, (int, float))
                or not math.isfinite(timeout_seconds)
                or timeout_seconds <= 0
            ):
                raise RewriteCloudflareRequestError(
                    "Timeout override must be a finite positive number."
                )

            effective_timeout = min(
                effective_timeout,
                float(timeout_seconds),
            )

        payload = {
            "messages": validated_messages,
            "max_tokens": CLOUDFLARE_MAX_TOKENS,
            "temperature": 0.1,
            "stream": False,
        }

        headers = {
            "Authorization": (
                f"Bearer {self._api_token.get_secret_value()}"
            ),
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(
                timeout=httpx.Timeout(effective_timeout),
            ) as client:
                response = client.post(
                    self._endpoint,
                    headers=headers,
                    json=payload,
                )

        except httpx.TimeoutException as exc:
            raise RewriteCloudflareTimeoutError(
                "Cloudflare request timed out."
            ) from exc

        except httpx.RequestError as exc:
            raise RewriteCloudflareConnectionError(
                "Unable to connect to Cloudflare."
            ) from exc

        try:
            body = response.json()

        except ValueError as exc:
            raise RewriteCloudflareResponseError(
                "Cloudflare returned invalid JSON."
            ) from exc

        error_code = self._extract_error_code(body)

        if response.status_code in {401, 403}:
            if response.status_code == 403 and error_code == 5035:
                raise RewriteCloudflarePaidPlanRequiredError(
                    "Cloudflare requires a paid plan for this request. "
                    "No paid upgrade will be attempted."
                )

            raise RewriteCloudflareAuthenticationError(
                "Cloudflare rejected the API credentials or access."
            )

        if response.status_code == 408:
            raise RewriteCloudflareTimeoutError(
                "Cloudflare request timed out."
            )

        if response.status_code == 429:
            if error_code == 3036:
                raise RewriteCloudflareQuotaExceededError(
                    "Cloudflare's daily free allocation is exhausted. "
                    "No paid upgrade will be attempted."
                )

            raise RewriteCloudflareRateLimitError(
                "Cloudflare rate limit or capacity limit reached."
            )

        if response.status_code >= 500:
            raise RewriteCloudflareServerError(
                "Cloudflare service returned a server error."
            )

        if response.status_code >= 400:
            raise RewriteCloudflareRequestError(
                "Cloudflare rejected the rewrite request."
            )

        if not isinstance(body, dict):
            raise RewriteCloudflareResponseError(
                "Cloudflare returned an unexpected response."
            )

        success = body.get("success")

        if success is False:
            raise RewriteCloudflareRequestError(
            "Cloudflare reported that the request was unsuccessful."
        )

        if success is not True:
            raise RewriteCloudflareResponseError(
            "Cloudflare response is missing a valid success indicator."
        )       

        result = body.get("result")

        if not isinstance(result, dict):
            raise RewriteCloudflareResponseError(
                "Cloudflare response is missing the result object."
            )

        choices = result.get("choices")

        if not isinstance(choices, list) or not choices:
            raise RewriteCloudflareResponseError(
                "Cloudflare response is missing generated choices."
            )

        first_choice = choices[0]

        if not isinstance(first_choice, dict):
            raise RewriteCloudflareResponseError(
                "Cloudflare returned an invalid choice."
            )

        message = first_choice.get("message")

        if not isinstance(message, dict):
            raise RewriteCloudflareResponseError(
                "Cloudflare response is missing the assistant message."
            )

        generated_text = message.get("content")

        if (
            not isinstance(generated_text, str)
            or not generated_text.strip()
        ):
            raise RewriteCloudflareResponseError(
                "Cloudflare returned empty or invalid generated text."
            )

        return generated_text.strip()
