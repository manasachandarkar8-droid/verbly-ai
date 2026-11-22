from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import Settings, get_settings


class RewriteRedisError(Exception):
    """Base exception for Feature 6 Redis failures."""


class RewriteRedisConfigurationError(RewriteRedisError):
    """Raised when Redis configuration is missing or invalid."""


class RewriteRedisUnavailableError(RewriteRedisError):
    """Raised when Redis cannot be reached."""


def create_rewrite_redis_client(
    redis_url: SecretStr,
) -> Redis:
    """
    Create a Redis client for Feature 6.

    Uses TLS when the supplied URL begins with rediss://.
    Credentials are never included in raised exception messages.
    """

    url = redis_url.get_secret_value().strip()

    if not url:
        raise RewriteRedisConfigurationError(
            "Feature 6 Redis URL is not configured."
        )

    if not url.startswith("rediss://"):
        raise RewriteRedisConfigurationError(
            "Feature 6 Redis requires a TLS connection."
        )

    try:
        return Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=5.0,
            socket_timeout=5.0,
            retry_on_timeout=False,
            health_check_interval=30,
        )

    except (RedisError, ValueError) as exc:
        raise RewriteRedisConfigurationError(
            "Feature 6 Redis connection configuration is invalid."
        ) from exc


@lru_cache(maxsize=1)
def get_rewrite_redis_client() -> Redis:
    """
    Return the shared Feature 6 Redis client.

    The client is initialized lazily and reused.
    Restart the backend after changing Redis configuration.
    """

    settings: Settings = get_settings()

    return create_rewrite_redis_client(
        settings.rewrite_redis_url
    )
