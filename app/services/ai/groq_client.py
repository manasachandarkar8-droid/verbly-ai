from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

import httpx
from pydantic import SecretStr
import math


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"


class GroqClientError(Exception):
    """Base exception for Groq client failures."""


class GroqConfigurationError(GroqClientError):
    """Raised when Groq configuration is missing or invalid."""


class GroqAuthenticationError(GroqClientError):
    """Raised when Groq rejects the API credentials."""


class GroqRateLimitError(GroqClientError):
    """Raised when the Groq rate limit is exceeded."""


class GroqTimeoutError(GroqClientError):
    """Raised when a Groq request times out."""


class GroqConnectionError(GroqClientError):
    """Raised when connection to Groq fails."""


class GroqServerError(GroqClientError):
    """Raised when Groq returns a server-side error."""


class GroqRequestError(GroqClientError):
    """Raised when Groq rejects the request."""


class GroqResponseError(GroqClientError):
    """Raised when Groq returns an invalid response."""


class GroqClient:
    """HTTP client for Groq structured-output requests."""

    def __init__(
        self,
        api_key: SecretStr,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._api_key = api_key.get_secret_value().strip()

        if not self._api_key:
            raise GroqConfigurationError(
                "Groq API key is not configured."
            )

        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError(
                "Timeout must be finite and greater than zero."
    )

        self._timeout_seconds = timeout_seconds
        self._timeout = httpx.Timeout(timeout_seconds)

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

        payload = {
            "model": GROQ_MODEL,
            "messages": list(messages),
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": json_schema,
                },
            },
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=request_timeout) as client:
                response = client.post(
                    GROQ_API_URL,
                    headers=headers,
                    json=payload,
                )

        except httpx.TimeoutException as exc:
            raise GroqTimeoutError(
                "Groq request timed out."
            ) from exc

        except httpx.RequestError as exc:
            raise GroqConnectionError(
                "Could not connect to Groq."
            ) from exc

        if response.status_code in (401, 403):
            raise GroqAuthenticationError(
                "Groq authentication failed. Check API credentials."
            )

        if response.status_code == 408:
            raise GroqTimeoutError(
                "Groq request timed out."
            )

        if response.status_code == 429:
            raise GroqRateLimitError(
                "Groq free-tier rate limit exceeded."
            )

        if response.status_code >= 500:
            raise GroqServerError(
                "Groq is temporarily unavailable."
            )

        if response.status_code >= 400:
            raise GroqRequestError(
                f"Groq rejected the request (HTTP {response.status_code})."
            )

        try:
            body = response.json()

            content = body["choices"][0]["message"]["content"]

            if not isinstance(content, str) or not content.strip():
                raise ValueError("Empty model response.")

            result = json.loads(content)

            if not isinstance(result, dict):
                raise ValueError("Expected a JSON object.")

            return result

        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise GroqResponseError(
                "Groq returned an invalid structured response."
            ) from exc