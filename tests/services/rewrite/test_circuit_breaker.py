from unittest.mock import MagicMock

import pytest

from redis.exceptions import ConnectionError as RedisConnectionError

from app.services.rewrite.circuit_breaker import (
    ABANDON_PROBE_SCRIPT,
    ALLOW_REQUEST_SCRIPT,
    CIRCUIT_KEY_PREFIX,
    RECORD_FAILURE_SCRIPT,
    RECORD_SUCCESS_SCRIPT,
    RewriteCircuitBreaker,
    RewriteCircuitOpenError,
    RewriteCircuitPermit,
    RewriteCircuitUnavailableError,
)


@pytest.fixture
def redis_client():
    return MagicMock()


@pytest.fixture
def breaker(redis_client):
    return RewriteCircuitBreaker(redis_client)


def test_approved_configuration(redis_client):
    breaker = RewriteCircuitBreaker(redis_client)

    assert breaker._failure_threshold == 3
    assert breaker._recovery_ms == 30_000
    assert breaker._probe_lease_ms == 90_000


def test_rejects_invalid_failure_threshold(redis_client):
    with pytest.raises(ValueError):
        RewriteCircuitBreaker(
            redis_client,
            failure_threshold=11,
        )


def test_rejects_invalid_recovery_duration(redis_client):
    with pytest.raises(ValueError):
        RewriteCircuitBreaker(
            redis_client,
            recovery_seconds=float("nan"),
        )


def test_rejects_invalid_probe_lease(redis_client):
    with pytest.raises(ValueError):
        RewriteCircuitBreaker(
            redis_client,
            probe_lease_seconds=60,
        )


def test_provider_keys_are_separate(breaker):
    groq_key = breaker._get_key("groq")
    cloudflare_key = breaker._get_key("cloudflare")

    assert groq_key == f"{CIRCUIT_KEY_PREFIX}:groq"
    assert cloudflare_key == f"{CIRCUIT_KEY_PREFIX}:cloudflare"
    assert groq_key != cloudflare_key


def test_rejects_unknown_provider(breaker):
    with pytest.raises(ValueError):
        breaker._get_key("unknown")


def test_closed_circuit_allows_request(breaker, redis_client):
    redis_client.eval.return_value = [1, "closed", 0, 0]

    permit = breaker.allow_request("groq")

    assert isinstance(permit, RewriteCircuitPermit)
    assert permit.provider == "groq"
    assert permit.generation == 0
    assert permit.is_probe is False


def test_open_circuit_rejects_request(breaker, redis_client):
    redis_client.eval.return_value = [0, "open", 1, 25_000]

    with pytest.raises(RewriteCircuitOpenError) as exc:
        breaker.allow_request("groq")

    assert exc.value.provider == "groq"
    assert exc.value.retry_after_ms == 25_000


def test_half_open_circuit_grants_probe(breaker, redis_client):
    redis_client.eval.return_value = [
        1,
        "half_open",
        1,
        "unique-probe-token",
        90_000,
    ]

    permit = breaker.allow_request("cloudflare")

    assert permit.provider == "cloudflare"
    assert permit.generation == 1
    assert permit.is_probe is True
    assert permit.probe_token == "unique-probe-token"


def test_malformed_redis_response_fails_closed(
    breaker,
    redis_client,
):
    redis_client.eval.return_value = "invalid"

    with pytest.raises(RewriteCircuitUnavailableError):
        breaker.allow_request("groq")


def test_redis_connection_failure_fails_closed(
    breaker,
    redis_client,
):
    redis_client.eval.side_effect = RedisConnectionError(
        "Redis unavailable"
    )

    with pytest.raises(RewriteCircuitUnavailableError):
        breaker.allow_request("groq")


def test_success_uses_atomic_script(breaker, redis_client):
    redis_client.eval.return_value = 1

    permit = RewriteCircuitPermit(
        provider="groq",
        generation=0,
    )

    assert breaker.record_success(permit) is True

    assert redis_client.eval.call_args.args[0] == RECORD_SUCCESS_SCRIPT


def test_failure_uses_atomic_script(breaker, redis_client):
    redis_client.eval.return_value = 1

    permit = RewriteCircuitPermit(
        provider="groq",
        generation=0,
    )

    assert breaker.record_failure(permit) is True

    assert redis_client.eval.call_args.args[0] == RECORD_FAILURE_SCRIPT


def test_abandon_probe_uses_atomic_script(breaker, redis_client):
    redis_client.eval.return_value = 1

    permit = RewriteCircuitPermit(
        provider="groq",
        generation=1,
        probe_token="probe-token",
    )

    assert breaker.abandon_probe(permit) is True

    assert redis_client.eval.call_args.args[0] == ABANDON_PROBE_SCRIPT


def test_cannot_abandon_normal_permit(breaker):
    permit = RewriteCircuitPermit(
        provider="groq",
        generation=0,
    )

    with pytest.raises(ValueError):
        breaker.abandon_probe(permit)


def test_stale_permit_returns_false(breaker, redis_client):
    redis_client.eval.return_value = 0

    permit = RewriteCircuitPermit(
        provider="groq",
        generation=0,
    )

    assert breaker.record_success(permit) is False
    assert breaker.record_failure(permit) is False


def test_redis_failure_during_state_update_fails_closed(
    breaker,
    redis_client,
):
    redis_client.eval.side_effect = RedisConnectionError(
        "Redis unavailable"
    )

    permit = RewriteCircuitPermit(
        provider="groq",
        generation=0,
    )

    with pytest.raises(RewriteCircuitUnavailableError):
        breaker.record_success(permit)


def test_redis_failure_during_probe_abandon_fails_closed(
    breaker,
    redis_client,
):
    redis_client.eval.side_effect = RedisConnectionError(
        "Redis unavailable"
    )

    permit = RewriteCircuitPermit(
        provider="groq",
        generation=1,
        probe_token="probe-token",
    )

    with pytest.raises(RewriteCircuitUnavailableError):
        breaker.abandon_probe(permit)


def test_lua_scripts_use_redis_server_time():
    scripts = (
        ALLOW_REQUEST_SCRIPT,
        RECORD_SUCCESS_SCRIPT,
        RECORD_FAILURE_SCRIPT,
        ABANDON_PROBE_SCRIPT,
    )

    for script in scripts:
        assert "redis.call('TIME')" in script


def test_lua_scripts_use_atomic_redis_operations():
    assert "HSET" in ALLOW_REQUEST_SCRIPT
    assert "HSET" in RECORD_FAILURE_SCRIPT
    assert "HDEL" in RECORD_SUCCESS_SCRIPT
    assert "probe_token" in ABANDON_PROBE_SCRIPT