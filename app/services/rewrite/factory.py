from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings

from app.services.rewrite.admission import (
    RewriteAdmissionController,
)

from app.services.rewrite.circuit_breaker import (
    RewriteCircuitBreaker,
)

from app.services.rewrite.cloudflare_client import (
    RewriteCloudflareClient,
)

from app.services.rewrite.groq_client import (
    RewriteGroqClient,
)

from app.services.rewrite.provider import (
    RewriteProvider,
)


from app.services.rewrite.redis_client import (
    get_rewrite_redis_client,
)



@lru_cache(maxsize=1)
def get_rewrite_admission_controller() -> RewriteAdmissionController:
    """Create and cache the distributed rewrite admission controller."""

    settings = get_settings()
    redis_client = get_rewrite_redis_client()

    return RewriteAdmissionController(
        redis_client,
        max_concurrency=settings.rewrite_max_concurrency,
        lease_ttl_seconds=settings.rewrite_lease_ttl_seconds,
    )


@lru_cache(maxsize=1)
def get_rewrite_circuit_breaker() -> RewriteCircuitBreaker:
    """Create and cache the provider-specific circuit breaker."""

    settings = get_settings()
    redis_client = get_rewrite_redis_client()

    return RewriteCircuitBreaker(
        redis_client,
        failure_threshold=settings.rewrite_circuit_failure_threshold,
        recovery_seconds=settings.rewrite_circuit_recovery_seconds,
        probe_lease_seconds=settings.rewrite_lease_ttl_seconds,
    )


@lru_cache(maxsize=1)
def get_rewrite_groq_client() -> RewriteGroqClient:
    """Create and cache the primary Groq client."""

    settings = get_settings()

    return RewriteGroqClient(
        api_key=settings.rewrite_groq_api_key,
        timeout_seconds=settings.rewrite_provider_timeout_seconds,
        read_timeout_seconds=settings.rewrite_groq_read_timeout_seconds,
    )


@lru_cache(maxsize=1)
def get_rewrite_cloudflare_client() -> RewriteCloudflareClient:
    """Create and cache the backup Cloudflare client."""

    settings = get_settings()

    return RewriteCloudflareClient(
        account_id=settings.rewrite_cloudflare_account_id,
        api_token=settings.rewrite_cloudflare_api_token,
        timeout_seconds=settings.rewrite_provider_timeout_seconds,
    )


@lru_cache(maxsize=1)
def get_rewrite_provider() -> RewriteProvider:
    """Create and cache the complete Feature 6 provider orchestrator."""

    settings = get_settings()

    return RewriteProvider(
        groq_client=get_rewrite_groq_client(),
        cloudflare_client=get_rewrite_cloudflare_client(),
        admission_controller=get_rewrite_admission_controller(),
        circuit_breaker=get_rewrite_circuit_breaker(),
        deadline_seconds=settings.rewrite_deadline_seconds,
    )

@lru_cache(maxsize=1)
def get_rewrite_service() -> RewriteService:
    """Create and cache the Feature 6 application service."""

    from app.services.rewrite.service import RewriteService

    return RewriteService(
        provider=get_rewrite_provider(),
    )

def close_rewrite_resources() -> None:
    """
    Close cached Feature 6 resources during application shutdown.

    Clears dependent cached objects before closing the shared
    Redis client. Does not initialize Redis if it was never used.
    """

    # Clear cached objects that depend on the Redis client.
    get_rewrite_service.cache_clear()
    get_rewrite_provider.cache_clear()
    get_rewrite_admission_controller.cache_clear()
    get_rewrite_circuit_breaker.cache_clear()
    get_rewrite_groq_client.cache_clear()
    get_rewrite_cloudflare_client.cache_clear()

    # Do not initialize Redis just to close it.
    if get_rewrite_redis_client.cache_info().currsize == 0:
        return

    redis_client = get_rewrite_redis_client()

    try:
        redis_client.close()
    finally:
        get_rewrite_redis_client.cache_clear()
