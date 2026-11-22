from __future__ import annotations

import secrets

from dataclasses import dataclass, field

from redis import Redis
from redis.exceptions import RedisError


ADMISSION_KEY = "verbly:feature6:rewrite:admission:leases"


ACQUIRE_LEASE_SCRIPT = """
local key = KEYS[1]
local token = ARGV[1]
local max_concurrency = tonumber(ARGV[2])
local lease_ttl_ms = tonumber(ARGV[3])
local key_ttl_ms = tonumber(ARGV[4])

-- Use Redis server time to avoid application clock differences.
local redis_time = redis.call('TIME')
local now_ms = tonumber(redis_time[1]) * 1000
    + math.floor(tonumber(redis_time[2]) / 1000)

-- Remove expired leases.
redis.call(
    'ZREMRANGEBYSCORE',
    key,
    '-inf',
    now_ms
)

-- Count currently active leases.
local active_count = redis.call('ZCARD', key)

-- Refresh key expiry so abandoned leases cannot persist indefinitely.
redis.call('PEXPIRE', key, key_ttl_ms)

if active_count >= max_concurrency then
    return 0
end

-- Store the unique token with its expiration timestamp.
local expires_at = now_ms + lease_ttl_ms

redis.call(
    'ZADD',
    key,
    expires_at,
    token
)

redis.call('PEXPIRE', key, key_ttl_ms)

return 1
"""


RELEASE_LEASE_SCRIPT = """
local key = KEYS[1]
local token = ARGV[1]

-- Only the owner of this unique token can release its lease.
local removed = redis.call('ZREM', key, token)

-- Delete the key when no leases remain.
if redis.call('ZCARD', key) == 0 then
    redis.call('DEL', key)
end

return removed
"""


class RewriteAdmissionError(Exception):
    """Base exception for rewrite admission failures."""


class RewriteCapacityExceededError(RewriteAdmissionError):
    """Raised when all rewrite execution slots are occupied."""


class RewriteAdmissionUnavailableError(RewriteAdmissionError):
    """Raised when Redis admission control is unavailable."""


@dataclass(frozen=True, slots=True)
class RewriteLease:
    """Represents ownership of one rewrite execution slot."""

    token: str = field(repr=False)


class RewriteAdmissionController:
    """Coordinates rewrite concurrency across backend workers."""

    def __init__(
        self,
        redis_client: Redis,
        *,
        max_concurrency: int = 2,
        lease_ttl_seconds: int = 90,
        key: str = ADMISSION_KEY,
    ) -> None:

        if not 1 <= max_concurrency <= 2:
            raise ValueError(
                "Rewrite concurrency must be between 1 and 2."
            )

        if not 76 <= lease_ttl_seconds <= 180:
            raise ValueError(
                "Rewrite lease must be between 76 and 180 seconds."
            )

        if not key.strip():
            raise ValueError("Admission key cannot be empty.")

        self._redis = redis_client
        self._max_concurrency = max_concurrency
        self._lease_ttl_ms = lease_ttl_seconds * 1000
        self._key_ttl_ms = (lease_ttl_seconds + 5) * 1000
        self._key = key

    def acquire(self) -> RewriteLease:
        """Atomically acquire a distributed rewrite execution slot."""

        token = secrets.token_urlsafe(32)

        try:
            result = self._redis.eval(
                ACQUIRE_LEASE_SCRIPT,
                1,
                self._key,
                token,
                self._max_concurrency,
                self._lease_ttl_ms,
                self._key_ttl_ms,
            )

        except RedisError as exc:
            raise RewriteAdmissionUnavailableError(
                "Rewrite admission control is temporarily unavailable."
            ) from exc

        if result == 0:
            raise RewriteCapacityExceededError(
                "All rewrite execution slots are currently occupied."
            )

        if result != 1:
            raise RewriteAdmissionUnavailableError(
                "Redis returned an unexpected admission result."
            )

        return RewriteLease(token=token)

    def release(self, lease: RewriteLease) -> bool:
        """
        Release a previously acquired lease.

        Returns False if the lease has already expired or was released.
        Releasing the same lease repeatedly is safe.
        """

        if not isinstance(lease, RewriteLease):
            raise TypeError("A valid rewrite lease is required.")

        try:
            result = self._redis.eval(
                RELEASE_LEASE_SCRIPT,
                1,
                self._key,
                lease.token,
            )

        except RedisError as exc:
            raise RewriteAdmissionUnavailableError(
                "Rewrite admission release is temporarily unavailable."
            ) from exc

        if result not in (0, 1):
            raise RewriteAdmissionUnavailableError(
                "Redis returned an unexpected release result."
            )

        return result == 1