from unittest.mock import MagicMock

import pytest

from redis.exceptions import ConnectionError as RedisConnectionError

from app.services.rewrite.admission import (
    ADMISSION_KEY,
    ACQUIRE_LEASE_SCRIPT,
    RELEASE_LEASE_SCRIPT,
    RewriteAdmissionController,
    RewriteAdmissionUnavailableError,
    RewriteCapacityExceededError,
    RewriteLease,
)


@pytest.fixture
def redis_client():
    return MagicMock()


@pytest.fixture
def controller(redis_client):
    return RewriteAdmissionController(
        redis_client,
        max_concurrency=2,
        lease_ttl_seconds=90,
    )


def test_controller_uses_approved_limits(redis_client):

    controller = RewriteAdmissionController(redis_client)

    assert controller._max_concurrency == 2
    assert controller._lease_ttl_ms == 90_000
    assert controller._key_ttl_ms == 95_000


def test_controller_rejects_invalid_concurrency(redis_client):

    with pytest.raises(ValueError):
        RewriteAdmissionController(
            redis_client,
            max_concurrency=3,
        )


def test_controller_rejects_unsafe_lease_duration(redis_client):

    with pytest.raises(ValueError):
        RewriteAdmissionController(
            redis_client,
            lease_ttl_seconds=60,
        )


def test_acquire_creates_unique_lease(controller, redis_client):

    redis_client.eval.return_value = 1

    lease = controller.acquire()

    assert isinstance(lease, RewriteLease)
    assert len(lease.token) >= 40

    redis_client.eval.assert_called_once()

    args = redis_client.eval.call_args.args

    assert args[0] == ACQUIRE_LEASE_SCRIPT
    assert args[1] == 1
    assert args[2] == ADMISSION_KEY
    assert args[3] == lease.token
    assert args[4] == 2
    assert args[5] == 90_000
    assert args[6] == 95_000


def test_acquire_rejects_when_capacity_is_full(
    controller,
    redis_client,
):

    redis_client.eval.return_value = 0

    with pytest.raises(RewriteCapacityExceededError):
        controller.acquire()


def test_acquire_uses_atomic_lua_script(controller, redis_client):

    redis_client.eval.return_value = 1

    controller.acquire()

    script = redis_client.eval.call_args.args[0]

    assert script == ACQUIRE_LEASE_SCRIPT
    assert "ZREMRANGEBYSCORE" in script
    assert "ZCARD" in script
    assert "ZADD" in script
    assert "TIME" in script


def test_release_uses_lease_token(controller, redis_client):

    redis_client.eval.return_value = 1

    lease = RewriteLease(token="test-lease-token")

    released = controller.release(lease)

    assert released is True

    args = redis_client.eval.call_args.args

    assert args[0] == RELEASE_LEASE_SCRIPT
    assert args[1] == 1
    assert args[2] == ADMISSION_KEY
    assert args[3] == "test-lease-token"


def test_release_is_idempotent(controller, redis_client):

    redis_client.eval.return_value = 0

    lease = RewriteLease(token="already-released")

    assert controller.release(lease) is False
    assert controller.release(lease) is False


def test_release_rejects_invalid_lease(controller):

    with pytest.raises(TypeError):
        controller.release("invalid-lease")


def test_redis_failure_fails_closed(controller, redis_client):

    redis_client.eval.side_effect = RedisConnectionError(
        "Redis unavailable"
    )

    with pytest.raises(RewriteAdmissionUnavailableError):
        controller.acquire()


def test_release_redis_failure_is_reported(
    controller,
    redis_client,
):

    redis_client.eval.side_effect = RedisConnectionError(
        "Redis unavailable"
    )

    lease = RewriteLease(token="test-token")

    with pytest.raises(RewriteAdmissionUnavailableError):
        controller.release(lease)


def test_lease_token_is_hidden_from_repr():

    lease = RewriteLease(token="sensitive-test-token")

    assert "sensitive-test-token" not in repr(lease)


def test_acquire_rejects_unexpected_redis_result(
    controller,
    redis_client,
):
    redis_client.eval.return_value = 2

    with pytest.raises(RewriteAdmissionUnavailableError):
        controller.acquire()


def test_release_rejects_unexpected_redis_result(
    controller,
    redis_client,
):
    redis_client.eval.return_value = 2

    lease = RewriteLease(token="test-token")

    with pytest.raises(RewriteAdmissionUnavailableError):
        controller.release(lease)

def test_acquire_generates_different_tokens(controller, redis_client):
    redis_client.eval.return_value = 1

    first_lease = controller.acquire()
    second_lease = controller.acquire()

    assert first_lease.token != second_lease.token

@pytest.mark.parametrize("invalid_result", [None, "invalid", [], {}])
def test_acquire_rejects_malformed_redis_results(
    controller,
    redis_client,
    invalid_result,
):
    redis_client.eval.return_value = invalid_result

    with pytest.raises(RewriteAdmissionUnavailableError):
        controller.acquire()

@pytest.mark.parametrize("invalid_result", [None, "invalid", [], {}])
def test_release_rejects_malformed_redis_results(
    controller,
    redis_client,
    invalid_result,
):
    redis_client.eval.return_value = invalid_result

    lease = RewriteLease(token="test-token")

    with pytest.raises(RewriteAdmissionUnavailableError):
        controller.release(lease)        

def test_acquired_lease_can_be_released(controller, redis_client):
    redis_client.eval.side_effect = [1, 1]

    lease = controller.acquire()
    released = controller.release(lease)

    assert released is True
    assert redis_client.eval.call_count == 2

    acquire_args = redis_client.eval.call_args_list[0].args
    release_args = redis_client.eval.call_args_list[1].args

    assert acquire_args[3] == lease.token
    assert release_args[3] == lease.token