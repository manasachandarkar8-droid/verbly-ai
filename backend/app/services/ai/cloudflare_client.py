from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

import httpx
from pydantic import SecretStr
import math


CLOUDFLARE_API_BASE = (
    "https://api.cloudflare.com/client/v4/accounts"
)

CLOUDFLARE_MODEL = (
    "@cf/google/gemma-4-26b-a4b-it"
)


class CloudflareClientError(Exception):
    """Base exception for Cloudflare client failures."""


class CloudflareConfigurationError(CloudflareClientError):
    """Raised when Cloudflare configuration is missing or invalid."""


class CloudflareAuthenticationError(CloudflareClientError):
    """Raised when Cloudflare rejects the API credentials."""


class CloudflarePaidPlanRequiredError(CloudflareClientError):
    """Raised when the requested model requires paid billing."""


class CloudflareQuotaExceededError(CloudflareClientError):
    """Raised when the free daily allocation is exhausted."""


class CloudflareRateLimitError(CloudflareClientError):
    """Raised when Cloudflare rate limits a request."""


class CloudflareTimeoutError(CloudflareClientError):
    """Raised when a Cloudflare request times out."""


class CloudflareConnectionError(CloudflareClientError):
    """Raised when connection to Cloudflare fails."""


class CloudflareServerError(CloudflareClientError):
    """Raised when Cloudflare returns a server-side error."""


class CloudflareRequestError(CloudflareClientError):
    """Raised when Cloudflare rejects a request."""


class CloudflareResponseError(CloudflareClientError):
    """Raised when Cloudflare returns an invalid response."""


class CloudflareClient:
    """HTTP client for Cloudflare Workers AI structured outputs."""

    def __init__(
        self,
        *,
        account_id: str,
        api_token: SecretStr,
        timeout_seconds: float = 30.0,
    ) -> None:

        normalized_account_id = account_id.strip()

        if (
            not normalized_account_id
            or "/" in normalized_account_id
            or "\\" in normalized_account_id
            or any(char.isspace() for char in normalized_account_id)
        ):
            raise CloudflareConfigurationError(
                "Cloudflare account ID is missing or invalid."
            )

        self._api_token = api_token.get_secret_value().strip()

        if not self._api_token:
            raise CloudflareConfigurationError(
                "Cloudflare API token is not configured."
            )

        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError(
                "Timeout must be finite and greater than zero."
            )

        self._endpoint = (
            f"{CLOUDFLARE_API_BASE}/"
            f"{normalized_account_id}/ai/v1/chat/completions"
        )

        self._timeout_seconds = timeout_seconds
        self._timeout = httpx.Timeout(timeout_seconds)
    
    @staticmethod
    def _extract_error_code(response: httpx.Response) -> int | None:
        """Extract Cloudflare's internal error code safely."""

        try:
            body = response.json()
        except ValueError:
            return None

        if not isinstance(body, dict):
            return None

        errors = body.get("errors", [])

        if isinstance(errors, list) and errors:
            first_error = errors[0]

            if isinstance(first_error, dict):
                code = first_error.get("code")

                try:
                    return int(code)
                except (TypeError, ValueError):
                    return None

        error = body.get("error")

        if isinstance(error, dict):
            code = error.get("code")

            try:
                return int(code)
            except (TypeError, ValueError):
                return None

        return None

    def create_structured_completion(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        schema_name: str,
        json_schema: dict[str, Any],
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:

        if timeout_seconds is not None:
            if (
                not math.isfinite(timeout_seconds)
                or timeout_seconds <= 0
            ):
                raise ValueError(
                    "Timeout must be finite and greater than zero."
        )

        effective_timeout = (
            self._timeout_seconds
            if timeout_seconds is None
            else min(self._timeout_seconds, timeout_seconds)
        )

        if not math.isfinite(effective_timeout) or effective_timeout <= 0:
            raise ValueError(
                "Timeout must be finite and greater than zero."
            )

        request_timeout = (
            self._timeout
            if timeout_seconds is None
            else httpx.Timeout(effective_timeout)
        )

        if not schema_name.strip():
            raise ValueError("Schema name cannot be empty.")

        request_messages = [
            dict(message) for message in messages
        ]

        schema_instruction = (
            f"Return a valid JSON object named {schema_name} "
            "that follows this JSON Schema exactly.\n"
            "Do not include Markdown fences, explanations, "
            "or additional text.\n"
            "If a value cannot be determined, use an appropriate "
            "empty value permitted by the schema.\n\n"
            "JSON Schema:\n"
            f"{json.dumps(json_schema, ensure_ascii=False)}"
        )

        system_message = next(
            (
                message
                for message in request_messages
                if message.get("role") == "system"
            ),
            None,
        )

        if system_message is not None:
            system_message["content"] += (
                "\n\n" + schema_instruction
            )
        else:
            request_messages.insert(
                0,
                {
                    "role": "system",
                    "content": schema_instruction,
                },
            )

        payload = {
            "model": CLOUDFLARE_MODEL,
            "messages": request_messages,
            "temperature": 0.1,
            "max_completion_tokens": 4096,
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=request_timeout) as client:
                response = client.post(
                    self._endpoint,
                    headers=headers,
                    json=payload,
                )

        except httpx.TimeoutException as exc:
            raise CloudflareTimeoutError(
                "Cloudflare request timed out."
            ) from exc

        except httpx.RequestError as exc:
            raise CloudflareConnectionError(
                "Could not connect to Cloudflare."
            ) from exc

        error_code = self._extract_error_code(response)

        if response.status_code == 401:
            raise CloudflareAuthenticationError(
                "Cloudflare authentication failed. "
                "Check API token permissions."
            )

        if response.status_code == 403:
            if error_code == 5035:
                raise CloudflarePaidPlanRequiredError(
                    "Cloudflare requires a paid plan for this model. "
                    "Paid usage is not permitted."
                )

            raise CloudflareAuthenticationError(
                "Cloudflare denied access. "
                "Check account permissions and model availability."
            )

        if response.status_code == 408:
            raise CloudflareTimeoutError(
                "Cloudflare request timed out."
            )

        if response.status_code == 429:
            if error_code == 3036:
                raise CloudflareQuotaExceededError(
                    "Cloudflare free daily allocation is exhausted."
                )

            raise CloudflareRateLimitError(
                "Cloudflare rate limit or capacity limit exceeded."
            )

        if response.status_code >= 500:
            raise CloudflareServerError(
                "Cloudflare is temporarily unavailable."
            )

        if response.status_code >= 400:
            raise CloudflareRequestError(
                f"Cloudflare rejected the request "
                f"(HTTP {response.status_code})."
            )

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]

            if not isinstance(content, str) or not content.strip():
                raise ValueError("Empty model response.")

            result = json.loads(content)

            if not isinstance(result, dict):
                raise ValueError("Expected a JSON object.")

            # Some Cloudflare model responses wrap the result
            # using the requested schema name.
            if schema_name in result:
                wrapped_result = result[schema_name]

                if not isinstance(wrapped_result, dict):
                    raise ValueError(
                        "Named structured response must contain a JSON object."
                )

                result = wrapped_result

            return result

        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise CloudflareResponseError(
                "Cloudflare returned an invalid structured response."
            ) from exc