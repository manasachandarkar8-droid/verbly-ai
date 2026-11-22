from __future__ import annotations
import logging
import math
import time


from collections.abc import Mapping, Sequence

from app.core.config import get_settings

from app.services.rewrite.admission import (
    RewriteAdmissionController,
)

from app.services.rewrite.circuit_breaker import (
    ProviderName,
    RewriteCircuitBreaker,
    RewriteCircuitOpenError,
)

from app.services.rewrite.cloudflare_client import (
    RewriteCloudflareClient,
    RewriteCloudflareConnectionError,
    RewriteCloudflareRateLimitError,
    RewriteCloudflareResponseError,
    RewriteCloudflareServerError,
    RewriteCloudflareTimeoutError,
)

from app.services.rewrite.groq_client import (
    RewriteGroqClient,
    RewriteGroqConnectionError,
    RewriteGroqRateLimitError,
    RewriteGroqResponseError,
    RewriteGroqServerError,
    RewriteGroqTimeoutError,
)

logger = logging.getLogger(__name__)

class RewriteProviderError(Exception):
    """Base exception for provider orchestration failures."""
    


class RewriteDeadlineExceededError(RewriteProviderError):
    """The overall rewrite execution deadline was exceeded."""


class RewriteProvidersUnavailableError(RewriteProviderError):
    """Neither configured provider can complete the rewrite."""


class RewriteProviderResponseError(RewriteProviderError):
    """A provider returned an unexpected result."""


GROQ_TRANSIENT_ERRORS = (
    RewriteGroqTimeoutError,
    RewriteGroqConnectionError,
    RewriteGroqRateLimitError,
    RewriteGroqServerError,
    RewriteGroqResponseError,
    RewriteProviderResponseError,
)

CLOUDFLARE_TRANSIENT_ERRORS = (
    RewriteCloudflareTimeoutError,
    RewriteCloudflareConnectionError,
    RewriteCloudflareRateLimitError,
    RewriteCloudflareServerError,
    RewriteCloudflareResponseError,
    RewriteProviderResponseError,
)


class RewriteProvider:
    """
    Coordinates Groq primary and Cloudflare backup.

    Uses distributed admission control and independent
    provider circuit breakers.

    No local inference or automatic retries are performed.
    """

    def __init__(
        self,
        *,
        groq_client: RewriteGroqClient,
        cloudflare_client: RewriteCloudflareClient,
        admission_controller: RewriteAdmissionController,
        circuit_breaker: RewriteCircuitBreaker,
        deadline_seconds: float = 75.0,
    ) -> None:

        if (
            isinstance(deadline_seconds, bool)
            or not isinstance(deadline_seconds, (int, float))
            or not math.isfinite(deadline_seconds)
            or deadline_seconds <= 0
        ):
            raise ValueError(
                "Rewrite deadline must be a finite positive number."
            )

        self._groq = groq_client
        self._cloudflare = cloudflare_client
        self._admission = admission_controller
        self._circuits = circuit_breaker
        self._deadline_seconds = float(deadline_seconds)


    @staticmethod
    def _validate_messages(
        messages: Sequence[Mapping[str, str]],
    ) -> list[dict[str, str]]:

        if (
            isinstance(messages, (str, bytes))
            or not isinstance(messages, Sequence)
            or not messages
        ):
            raise ValueError(
                "At least one rewrite message is required."
            )

        validated: list[dict[str, str]] = []

        # Use roles supported by BOTH configured providers.
        for message in messages:
            if not isinstance(message, Mapping):
                raise ValueError(
                    "Every rewrite message must be a mapping."
                )

            role = message.get("role")
            content = message.get("content")

            if (
                not isinstance(role, str)
                or role not in {"system", "user", "assistant"}
            ):
                raise ValueError(
                    "Unsupported rewrite message role."
                )

            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    "Rewrite message content cannot be empty."
                )

            validated.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        return validated
   
    @staticmethod
    def _remaining_time(deadline: float) -> float:

        remaining = deadline - time.monotonic()

        if remaining <= 0:
            raise RewriteDeadlineExceededError(
                "The rewrite execution deadline was exceeded."
            )

        return remaining

    @staticmethod
    def _is_transient(
        provider: ProviderName,
        error: Exception,
    ) -> bool:

        if provider == "groq":
            return isinstance(error, GROQ_TRANSIENT_ERRORS)

        if provider == "cloudflare":
            return isinstance(error, CLOUDFLARE_TRANSIENT_ERRORS)

        return False

    def _abandon_probe_if_needed(
        self,
        permit,
    ) -> None:

        if permit.is_probe:
            self._circuits.abandon_probe(permit)

    def _execute_provider(
        self,
        *,
        provider: ProviderName,
        client,
        messages: list[dict[str, str]],
        deadline: float,
    ) -> str:
        

        # Check deadline before requesting circuit permission.
        self._remaining_time(deadline)

        permit = self._circuits.allow_request(provider)

        try:
            remaining = self._remaining_time(deadline)

            result = client.rewrite(
                messages=messages,
                timeout_seconds=remaining,
            )

            if not isinstance(result, str) or not result.strip():
                raise RewriteProviderResponseError(
                    "Provider returned an empty rewrite."
                )

                        # Enforce the overall deadline after receiving the response.
            self._remaining_time(deadline)

        except Exception as exc:

            if self._is_transient(provider, exc):
                # Only eligible transient failures affect circuit state.
                self._circuits.record_failure(permit)

            else:
                # Do not leave a half-open probe locked.
                self._abandon_probe_if_needed(permit)

            raise

        # Record success only after receiving valid generated text.
        self._circuits.record_success(permit)

        logger.info(
            "Rewrite completed successfully using provider: %s",
            provider,
        )

        return result.strip()

    def rewrite(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
    ) -> str:

        validated_messages = self._validate_messages(messages)

        deadline = (
            time.monotonic() + self._deadline_seconds
        )

        # Acquire one distributed execution slot.
        lease = self._admission.acquire()

        try:
            # Ensure admission acquisition did not consume the deadline.
            self._remaining_time(deadline)

            # -----------------------------------------
            # PRIMARY PROVIDER: GROQ
            # -----------------------------------------

            try:
                return self._execute_provider(
                    provider="groq",
                    client=self._groq,
                    messages=validated_messages,
                    deadline=deadline,
                )

            except RewriteCircuitOpenError as exc:

                if exc.provider != "groq":
                    raise

                logger.warning(
                    "Groq circuit is open. Attempting Cloudflare fallback."
                )

            except GROQ_TRANSIENT_ERRORS as exc:

                logger.warning(
                    "Groq transient failure (%s). Attempting Cloudflare fallback.",
                    type(exc).__name__,
                )

            # -----------------------------------------
            # BACKUP PROVIDER: CLOUDFLARE
            # -----------------------------------------

            try:
                return self._execute_provider(
                    provider="cloudflare",
                    client=self._cloudflare,
                    messages=validated_messages,
                    deadline=deadline,
                )

            except RewriteCircuitOpenError as exc:

                if exc.provider != "cloudflare":
                    raise

                raise RewriteProvidersUnavailableError(
                    "Both rewrite providers are unavailable."
                ) from exc

            except CLOUDFLARE_TRANSIENT_ERRORS as exc:

                logger.error(
                    "Cloudflare backup failed with transient error: %s",
                    type(exc).__name__,
                )

                raise RewriteProvidersUnavailableError(
                    "Groq and Cloudflare could not complete "
                    "the rewrite."
                ) from exc

        finally:
            # Always release the distributed admission lease.
            self._admission.release(lease)