from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from pydantic import ValidationError

from app.schemas.content_analysis_ai import ContentAnalysisAIResponse

from app.services.ai.groq_client import (
    GroqClient,
    GroqConfigurationError,
    GroqAuthenticationError,
    GroqRateLimitError,
    GroqTimeoutError,
    GroqConnectionError,
    GroqServerError,
    GroqRequestError,
    GroqResponseError,
)

from app.services.ai.cloudflare_client import (
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

from time import monotonic

class AIProviderError(Exception):
    """Base exception for AI provider orchestration failures."""


class AIProviderConfigurationError(AIProviderError):
    """Raised when provider configuration or authentication fails."""


class AIProviderUnavailableError(AIProviderError):
    """Raised when neither provider can complete the analysis."""


class AIProviderQuotaExceededError(AIProviderError):
    """Raised when the backup provider's free quota is exhausted."""


class AIProviderPaidPlanRequiredError(AIProviderError):
    """Raised when the backup provider requires paid usage."""


class AIProviderRequestError(AIProviderError):
    """Raised when a provider rejects the analysis request."""

class AIProviderDeadlineExceededError(AIProviderError):
    """Raised when the overall analysis deadline expires."""

class AIProvider:
    """
    Coordinates Groq as the primary provider and Cloudflare as backup.

    Both clients are initialized lazily. Cloudflare is only initialized
    when an eligible Groq failure requires fallback.

    Provider responses are independently validated using Pydantic.
    """

    def __init__(
        self,
        *,
        groq_client_factory: Callable[[], GroqClient],
        cloudflare_client_factory: Callable[[], CloudflareClient],
    ) -> None:
        self._groq_client_factory = groq_client_factory
        self._cloudflare_client_factory = cloudflare_client_factory

        self._groq_client: GroqClient | None = None
        self._cloudflare_client: CloudflareClient | None = None

    def _get_groq_client(self) -> GroqClient:
        if self._groq_client is None:
            self._groq_client = self._groq_client_factory()

        return self._groq_client

    def _get_cloudflare_client(self) -> CloudflareClient:
        if self._cloudflare_client is None:
            self._cloudflare_client = (
                self._cloudflare_client_factory()
            )

        return self._cloudflare_client

    @staticmethod
    def _request_and_validate(
        client: GroqClient | CloudflareClient,
        *,
        messages: Sequence[Mapping[str, str]],
        schema_name: str,
        json_schema: dict[str, Any],
        timeout_seconds: float | None = None,
    ) -> ContentAnalysisAIResponse:

        raw_response = client.create_structured_completion(
            messages=messages,
            schema_name=schema_name,
            json_schema=json_schema,
            timeout_seconds=timeout_seconds,
        )

        return ContentAnalysisAIResponse.model_validate(
            raw_response
        )

    def _get_remaining_timeout(
        self,
        deadline: float | None,
    ) -> float | None:
        """Return the remaining time before the analysis deadline."""

        if deadline is None:
            return None

        remaining = deadline - monotonic()

        if remaining <= 0:
            raise AIProviderDeadlineExceededError(
                "The content analysis deadline has expired."
            )

        return remaining

    def analyze(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        schema_name: str,
        json_schema: dict[str, Any],
        deadline: float | None = None,
    ) -> ContentAnalysisAIResponse:
        """
        Attempt Groq first and use Cloudflare only for eligible failures.

        Invalid credentials, missing configuration and rejected requests
        do not trigger fallback.
        """

        try:
            remaining_timeout = self._get_remaining_timeout(deadline)

            print("[AI PROVIDER] Attempting Groq (primary).")
            response = self._request_and_validate(
                self._get_groq_client(),
                messages=messages,
                schema_name=schema_name,
                json_schema=json_schema,
                timeout_seconds=remaining_timeout,
            )

            # Reject a response that arrives after the overall deadline.
            self._get_remaining_timeout(deadline)

            return response

        except (
            GroqRateLimitError,
            GroqTimeoutError,
            GroqConnectionError,
            GroqServerError,
            GroqResponseError,
            ValidationError,
        ): 
            return self._try_cloudflare(
                messages=messages,
                schema_name=schema_name,
                json_schema=json_schema,
                deadline=deadline,
            )

        except (
            GroqConfigurationError,
            GroqAuthenticationError,
        ) as exc:
            raise AIProviderConfigurationError(
                "Primary AI provider configuration or authentication failed."
            ) from exc

        except GroqRequestError as exc:
            raise AIProviderRequestError(
                "Primary AI provider rejected the request."
            ) from exc

    def _try_cloudflare(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        schema_name: str,
        json_schema: dict[str, Any],
        deadline: float | None = None,
    ) -> ContentAnalysisAIResponse:
        """Attempt the backup provider after an eligible Groq failure."""

        try:
            remaining_timeout = self._get_remaining_timeout(deadline)
            print("[AI PROVIDER] Attempting Cloudflare (backup).")
            response = self._request_and_validate(
                self._get_cloudflare_client(),
                messages=messages,
                schema_name=schema_name,
                json_schema=json_schema,
                timeout_seconds=remaining_timeout,
            )

            # Reject a response that arrives after the overall deadline.
            self._get_remaining_timeout(deadline)

            return response

        except AIProviderDeadlineExceededError:
            raise

        except CloudflarePaidPlanRequiredError as exc:
            raise AIProviderPaidPlanRequiredError(
                "Backup provider requires paid usage. "
                "Paid usage is disabled."
            ) from exc

        except CloudflareQuotaExceededError as exc:
            raise AIProviderQuotaExceededError(
                "Backup provider free quota is exhausted."
            ) from exc

        except (
            CloudflareConfigurationError,
            CloudflareAuthenticationError,
        ) as exc:
            raise AIProviderConfigurationError(
                "Backup AI provider configuration or authentication failed."
            ) from exc

        except CloudflareRequestError as exc:
            raise AIProviderRequestError(
                "Backup AI provider rejected the request."
            ) from exc

        except (
            CloudflareRateLimitError,
            CloudflareTimeoutError,
            CloudflareConnectionError,
            CloudflareServerError,
            CloudflareResponseError,
            ValidationError,
        ) as exc:
            raise AIProviderUnavailableError(
                "Both AI providers failed to complete the analysis."
            ) from exc