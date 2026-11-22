from __future__ import annotations

import math
import secrets

from dataclasses import dataclass, field
from typing import Literal

from redis import Redis
from redis.exceptions import RedisError


ProviderName = Literal["groq", "cloudflare"]

ALLOWED_PROVIDERS = frozenset({"groq", "cloudflare"})

CIRCUIT_KEY_PREFIX = "verbly:feature6:rewrite:circuit"

CIRCUIT_KEY_TTL_SECONDS = 86_400


ALLOW_REQUEST_SCRIPT = """
local key = KEYS[1]
local token = ARGV[1]
local recovery_ms = tonumber(ARGV[2])
local probe_lease_ms = tonumber(ARGV[3])
local key_ttl = tonumber(ARGV[4])

local redis_time = redis.call('TIME')
local now_ms = tonumber(redis_time[1]) * 1000
    + math.floor(tonumber(redis_time[2]) / 1000)

local state = redis.call('HGET', key, 'state') or 'closed'
local generation = tonumber(
    redis.call('HGET', key, 'generation') or '0'
)

if state ~= 'closed'
    and state ~= 'open'
    and state ~= 'half_open' then
    return {-1, 'invalid', generation, 0}
end

if state == 'open' then
    local open_until = tonumber(
        redis.call('HGET', key, 'open_until_ms') or '0'
    )

    if now_ms < open_until then
        redis.call('EXPIRE', key, key_ttl)

        return {
            0,
            'open',
            generation,
            open_until - now_ms
        }
    end

    state = 'half_open'

    redis.call(
        'HSET',
        key,
        'state',
        'half_open'
    )
end

if state == 'half_open' then
    local probe_expires = tonumber(
        redis.call('HGET', key, 'probe_expires_at_ms') or '0'
    )

    local current_token = redis.call(
        'HGET',
        key,
        'probe_token'
    )

    if current_token and now_ms < probe_expires then
        redis.call('EXPIRE', key, key_ttl)

        return {
            0,
            'half_open',
            generation,
            probe_expires - now_ms
        }
    end

    redis.call(
        'HSET',
        key,
        'state',
        'half_open',
        'probe_token',
        token,
        'probe_expires_at_ms',
        now_ms + probe_lease_ms
    )

    redis.call('EXPIRE', key, key_ttl)

    return {
        1,
        'half_open',
        generation,
        token,
        probe_lease_ms
    }
end

redis.call('EXPIRE', key, key_ttl)

return {
    1,
    'closed',
    generation,
    0
}
"""


RECORD_SUCCESS_SCRIPT = """
local key = KEYS[1]
local permit_generation = tonumber(ARGV[1])
local probe_token = ARGV[2]
local key_ttl = tonumber(ARGV[3])

local redis_time = redis.call('TIME')
local now_ms = tonumber(redis_time[1]) * 1000
    + math.floor(tonumber(redis_time[2]) / 1000)

local state = redis.call('HGET', key, 'state') or 'closed'
local generation = tonumber(
    redis.call('HGET', key, 'generation') or '0'
)

if generation ~= permit_generation then
    return 0
end

if probe_token ~= '' then
    local current_token = redis.call(
        'HGET',
        key,
        'probe_token'
    )

    local probe_expires = tonumber(
        redis.call('HGET', key, 'probe_expires_at_ms') or '0'
    )

    if state ~= 'half_open'
        or current_token ~= probe_token
        or now_ms >= probe_expires then
        return 0
    end

    redis.call(
        'HSET',
        key,
        'state',
        'closed',
        'failure_count',
        0,
        'open_until_ms',
        0
    )

    redis.call(
        'HDEL',
        key,
        'probe_token',
        'probe_expires_at_ms'
    )

    redis.call('EXPIRE', key, key_ttl)

    return 1
end

if state ~= 'closed' then
    return 0
end

redis.call(
    'HSET',
    key,
    'failure_count',
    0
)

redis.call('EXPIRE', key, key_ttl)

return 1
"""


RECORD_FAILURE_SCRIPT = """
local key = KEYS[1]
local permit_generation = tonumber(ARGV[1])
local probe_token = ARGV[2]
local failure_threshold = tonumber(ARGV[3])
local recovery_ms = tonumber(ARGV[4])
local key_ttl = tonumber(ARGV[5])

local redis_time = redis.call('TIME')
local now_ms = tonumber(redis_time[1]) * 1000
    + math.floor(tonumber(redis_time[2]) / 1000)

local state = redis.call('HGET', key, 'state') or 'closed'
local generation = tonumber(
    redis.call('HGET', key, 'generation') or '0'
)

if generation ~= permit_generation then
    return 0
end

if probe_token ~= '' then
    local current_token = redis.call(
        'HGET',
        key,
        'probe_token'
    )

    local probe_expires = tonumber(
        redis.call('HGET', key, 'probe_expires_at_ms') or '0'
    )

    if state ~= 'half_open'
        or current_token ~= probe_token
        or now_ms >= probe_expires then
        return 0
    end

    redis.call(
        'HSET',
        key,
        'state',
        'open',
        'failure_count',
        failure_threshold,
        'open_until_ms',
        now_ms + recovery_ms,
        'generation',
        generation + 1
    )

    redis.call(
        'HDEL',
        key,
        'probe_token',
        'probe_expires_at_ms'
    )

    redis.call('EXPIRE', key, key_ttl)

    return 1
end

if state ~= 'closed' then
    return 0
end

local failures = tonumber(
    redis.call('HGET', key, 'failure_count') or '0'
)

failures = failures + 1

if failures >= failure_threshold then
    redis.call(
        'HSET',
        key,
        'state',
        'open',
        'failure_count',
        failures,
        'open_until_ms',
        now_ms + recovery_ms,
        'generation',
        generation + 1
    )
else
    redis.call(
        'HSET',
        key,
        'failure_count',
        failures
    )
end

redis.call('EXPIRE', key, key_ttl)

return 1
"""


ABANDON_PROBE_SCRIPT = """
local key = KEYS[1]
local permit_generation = tonumber(ARGV[1])
local probe_token = ARGV[2]
local recovery_ms = tonumber(ARGV[3])
local key_ttl = tonumber(ARGV[4])

local redis_time = redis.call('TIME')
local now_ms = tonumber(redis_time[1]) * 1000
    + math.floor(tonumber(redis_time[2]) / 1000)

local state = redis.call('HGET', key, 'state') or 'closed'
local generation = tonumber(
    redis.call('HGET', key, 'generation') or '0'
)

local current_token = redis.call(
    'HGET',
    key,
    'probe_token'
)

local probe_expires = tonumber(
    redis.call('HGET', key, 'probe_expires_at_ms') or '0'
)

if state ~= 'half_open'
    or generation ~= permit_generation
    or current_token ~= probe_token
    or now_ms >= probe_expires then
    return 0
end

redis.call(
    'HSET',
    key,
    'state',
    'open',
    'open_until_ms',
    now_ms + recovery_ms,
    'generation',
    generation + 1
)

redis.call(
    'HDEL',
    key,
    'probe_token',
    'probe_expires_at_ms'
)

redis.call('EXPIRE', key, key_ttl)

return 1
"""


class RewriteCircuitError(Exception):
    """Base exception for rewrite circuit-breaker errors."""


class RewriteCircuitOpenError(RewriteCircuitError):
    """Raised when a provider circuit does not permit a request."""

    def __init__(
        self,
        provider: str,
        retry_after_ms: int,
    ) -> None:
        self.provider = provider
        self.retry_after_ms = max(0, retry_after_ms)

        super().__init__(
            f"The {provider} provider circuit is not accepting requests."
        )


class RewriteCircuitUnavailableError(RewriteCircuitError):
    """Raised when circuit-breaker state cannot be accessed safely."""


@dataclass(frozen=True, slots=True)
class RewriteCircuitPermit:
    """Represents permission to execute one provider request."""

    provider: str
    generation: int
    probe_token: str | None = field(default=None, repr=False)

    @property
    def is_probe(self) -> bool:
        return self.probe_token is not None


class RewriteCircuitBreaker:
    """Coordinates independent provider circuit breakers using Redis."""

    def __init__(
        self,
        redis_client: Redis,
        *,
        failure_threshold: int = 3,
        recovery_seconds: float = 30.0,
        probe_lease_seconds: int = 90,
        key_prefix: str = CIRCUIT_KEY_PREFIX,
    ) -> None:

        if not 1 <= failure_threshold <= 10:
            raise ValueError(
                "Failure threshold must be between 1 and 10."
            )

        if (
            not math.isfinite(recovery_seconds)
            or not 0.0 < recovery_seconds <= 300.0
        ):
            raise ValueError(
                "Recovery duration must be greater than 0 "
                "and at most 300 seconds."
            )

        if not 76 <= probe_lease_seconds <= 180:
            raise ValueError(
                "Probe lease must be between 76 and 180 seconds."
            )

        if not key_prefix.strip():
            raise ValueError("Circuit key prefix cannot be empty.")

        self._redis = redis_client
        self._failure_threshold = failure_threshold
        self._recovery_ms = math.ceil(recovery_seconds * 1000)
        self._probe_lease_ms = probe_lease_seconds * 1000
        self._key_prefix = key_prefix.rstrip(":")

    def _get_key(self, provider: str) -> str:
        if provider not in ALLOWED_PROVIDERS:
            raise ValueError("Unsupported rewrite provider.")

        return f"{self._key_prefix}:{provider}"

    @staticmethod
    def _validate_script_result(result: object) -> int:
        if isinstance(result, bool) or not isinstance(result, int):
            raise RewriteCircuitUnavailableError(
                "Redis returned an unexpected circuit result."
            )

        if result not in (0, 1):
            raise RewriteCircuitUnavailableError(
                "Redis returned an invalid circuit result."
            )

        return result

    def allow_request(
        self,
        provider: ProviderName,
    ) -> RewriteCircuitPermit:
        """Check circuit state and obtain permission for a provider request."""

        key = self._get_key(provider)
        token = secrets.token_urlsafe(32)

        try:
            result = self._redis.eval(
                ALLOW_REQUEST_SCRIPT,
                1,
                key,
                token,
                self._recovery_ms,
                self._probe_lease_ms,
                CIRCUIT_KEY_TTL_SECONDS,
            )

        except RedisError as exc:
            raise RewriteCircuitUnavailableError(
                "Provider circuit state is temporarily unavailable."
            ) from exc

        if not isinstance(result, (list, tuple)) or len(result) < 4:
            raise RewriteCircuitUnavailableError(
                "Redis returned an invalid circuit response."
            )

        try:
            status = int(result[0])
            state = str(result[1])
            generation = int(result[2])
        except (TypeError, ValueError, OverflowError, IndexError) as exc:
            raise RewriteCircuitUnavailableError(
                "Redis returned malformed circuit data."
            ) from exc

        if status == -1:
            raise RewriteCircuitUnavailableError(
                "Redis contains an invalid provider circuit state."
            )

        if status == 0:
            try:
                retry_after_ms = int(result[3])
            except (TypeError, ValueError, OverflowError, IndexError) as exc:
                raise RewriteCircuitUnavailableError(
                    "Redis returned invalid retry information."
                ) from exc

            return self._raise_circuit_open(
                provider,
                retry_after_ms,
            )

        if status != 1:
            raise RewriteCircuitUnavailableError(
                "Redis returned an unexpected admission status."
            )

        if state == "closed" and len(result) == 4:
            return RewriteCircuitPermit(
                provider=provider,
                generation=generation,
            )

        if state == "half_open" and len(result) == 5:
            probe_token = str(result[3])

            try:
                probe_lease_ms = int(result[4])
            except (TypeError, ValueError, OverflowError) as exc:
                raise RewriteCircuitUnavailableError(
                    "Redis returned invalid probe lease information."
                ) from exc

            if not probe_token or probe_lease_ms <= 0:
                raise RewriteCircuitUnavailableError(
                    "Redis returned an invalid probe permit."
                )

            return RewriteCircuitPermit(
                provider=provider,
                generation=generation,
                probe_token=probe_token,
            )

        raise RewriteCircuitUnavailableError(
            "Redis returned an inconsistent circuit state."
        )

    def record_success(
        self,
        permit: RewriteCircuitPermit,
    ) -> bool:
        """Record a successful request if the permit is still valid."""

        key = self._get_key(permit.provider)

        try:
            result = self._redis.eval(
                RECORD_SUCCESS_SCRIPT,
                1,
                key,
                permit.generation,
                permit.probe_token or "",
                CIRCUIT_KEY_TTL_SECONDS,
            )

        except RedisError as exc:
            raise RewriteCircuitUnavailableError(
                "Unable to update provider circuit state."
            ) from exc

        return bool(self._validate_script_result(result))

    def record_failure(
        self,
        permit: RewriteCircuitPermit,
    ) -> bool:
        """
        Record an eligible transient provider failure.

        The caller must classify the exception before invoking this method.
        Authentication, configuration and invalid-request failures must not
        be counted.
        """

        key = self._get_key(permit.provider)

        try:
            result = self._redis.eval(
                RECORD_FAILURE_SCRIPT,
                1,
                key,
                permit.generation,
                permit.probe_token or "",
                self._failure_threshold,
                self._recovery_ms,
                CIRCUIT_KEY_TTL_SECONDS,
            )

        except RedisError as exc:
            raise RewriteCircuitUnavailableError(
                "Unable to update provider circuit state."
            ) from exc

        return bool(self._validate_script_result(result))

    def abandon_probe(
        self,
        permit: RewriteCircuitPermit,
    ) -> bool:
        """Safely abandon a half-open probe after cancellation."""

        if not permit.is_probe:
            raise ValueError(
                "Only a half-open probe permit can be abandoned."
            )

        key = self._get_key(permit.provider)

        try:
            result = self._redis.eval(
                ABANDON_PROBE_SCRIPT,
                1,
                key,
                permit.generation,
                permit.probe_token,
                self._recovery_ms,
                CIRCUIT_KEY_TTL_SECONDS,
            )

        except RedisError as exc:
            raise RewriteCircuitUnavailableError(
                "Unable to abandon provider recovery probe."
            ) from exc

        return bool(self._validate_script_result(result))


    @staticmethod
    def _raise_circuit_open(
        provider: str,
        retry_after_ms: int,
    ) -> None:
        raise RewriteCircuitOpenError(
            provider,
            retry_after_ms,
        )    