from __future__ import annotations

import math
from typing import Mapping, Sequence

import httpx
from pydantic import SecretStr


GROQ_REWRITE_API_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

GROQ_REWRITE_MODEL = "openai/gpt-oss-120b"

GROQ_MAX_COMPLETION_TOKENS = 4096


class RewriteGroqError(Exception):
    """Base exception for Feature 6 Groq failures."""


class RewriteGroqConfigurationError(RewriteGroqError):
    """Invalid or missing Groq configuration."""


class RewriteGroqAuthenticationError(RewriteGroqError):
    """Groq authentication failure."""


class RewriteGroqRateLimitError(RewriteGroqError):
    """Groq rate limit exceeded."""


class RewriteGroqTimeoutError(RewriteGroqError):
    """Groq request timed out."""


class RewriteGroqConnectionError(RewriteGroqError):
    """Connection to Groq failed."""


class RewriteGroqServerError(RewriteGroqError):
    """Groq server-side failure."""


class RewriteGroqRequestError(RewriteGroqError):
    """Groq rejected the request."""


class RewriteGroqResponseError(RewriteGroqError):
    """Groq returned an invalid or incomplete response."""


class RewriteGroqClient:
    """External Groq API client for Feature 6."""

    def __init__(
        self,
        *,
        api_key: SecretStr,
        timeout_seconds: float = 80.0,
        read_timeout_seconds: float = 30.0,
    ) -> None:

        api_key_value = api_key.get_secret_value().strip()

        if not api_key_value:
            raise RewriteGroqConfigurationError(
                "Groq API key is not configured."
            )

        if (
            not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError(
                "Timeout must be finite and greater than zero."
            )

        if (
            not math.isfinite(read_timeout_seconds)
            or read_timeout_seconds <= 0
        ):
            raise ValueError(
                "Read timeout must be finite and greater than zero."
            )

        self._api_key = api_key_value
        self._timeout_seconds = timeout_seconds
        self._read_timeout_seconds = read_timeout_seconds

    def rewrite(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        timeout_seconds: float | None = None,
    ) -> str:

        if not messages:
            raise ValueError("Messages cannot be empty.")

        if timeout_seconds is not None:
            if (
                not math.isfinite(timeout_seconds)
                or timeout_seconds <= 0
            ):
                raise ValueError(
                    "Timeout must be finite and greater than zero."
                )

        request_messages = []

        for message in messages:
            if not isinstance(message, Mapping):
                raise ValueError("Invalid message format.")

            role = message.get("role")
            content = message.get("content")

            if role not in {
                "system",
                "developer",
                "user",
                "assistant",
            }:
                raise ValueError("Invalid message role.")

            if not isinstance(content, str) or not content.strip():
                raise ValueError("Message content cannot be empty.")

            request_messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        effective_timeout = (
            self._timeout_seconds
            if timeout_seconds is None
            else min(
                self._timeout_seconds,
                timeout_seconds,
            )
        )

        effective_read_timeout = min(
            self._read_timeout_seconds,
            effective_timeout,
        )

        request_timeout = httpx.Timeout(
            effective_timeout,
            read=effective_read_timeout,
        )

        payload = {
            "model": GROQ_REWRITE_MODEL,
            "messages": request_messages,
            "max_completion_tokens": GROQ_MAX_COMPLETION_TOKENS,
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=request_timeout) as client:
                response = client.post(
                    GROQ_REWRITE_API_URL,
                    headers=headers,
                    json=payload,
                )

        except httpx.TimeoutException as exc:
            raise RewriteGroqTimeoutError(
                "Groq request timed out."
            ) from exc

        except httpx.RequestError as exc:
            raise RewriteGroqConnectionError(
                "Could not connect to Groq."
            ) from exc

        if response.status_code in (401, 403):
            raise RewriteGroqAuthenticationError(
                "Groq authentication failed."
            )

        if response.status_code == 408:
            raise RewriteGroqTimeoutError(
                "Groq request timed out."
            )

        if response.status_code == 429:
            raise RewriteGroqRateLimitError(
                "Groq rate limit exceeded."
            )

        if response.status_code >= 500:
            raise RewriteGroqServerError(
                "Groq is temporarily unavailable."
            )

        if response.status_code >= 400:
            raise RewriteGroqRequestError(
                f"Groq rejected the request "
                f"(HTTP {response.status_code})."
            )

        try:
            body = response.json()

            choices = body["choices"]

            if not isinstance(choices, list) or not choices:
                raise ValueError("Missing completion choices.")

            choice = choices[0]

            if choice.get("finish_reason") == "length":
                raise ValueError("Completion was truncated.")

            message = choice["message"]
            content = message["content"]

            if not isinstance(content, str) or not content.strip():
                raise ValueError("Empty model response.")

            return content.strip()

        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise RewriteGroqResponseError(
                "Groq returned an invalid or incomplete response."
            ) from exc