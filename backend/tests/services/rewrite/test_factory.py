from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from app.services.rewrite import factory


@pytest.fixture
def settings(monkeypatch):
    mock_settings = MagicMock()

    mock_settings.rewrite_max_concurrency = 2
    mock_settings.rewrite_lease_ttl_seconds = 90
    mock_settings.rewrite_circuit_failure_threshold = 3
    mock_settings.rewrite_circuit_recovery_seconds = 30.0

    mock_settings.rewrite_groq_api_key = SecretStr("test-groq-key")
    mock_settings.rewrite_cloudflare_account_id = "a" * 32
    mock_settings.rewrite_cloudflare_api_token = SecretStr(
        "test-cloudflare-token"
    )

    mock_settings.rewrite_provider_timeout_seconds = 80.0
    mock_settings.rewrite_groq_read_timeout_seconds = 30.0
    mock_settings.rewrite_deadline_seconds = 75.0

    monkeypatch.setattr(
        factory,
        "get_settings",
        lambda: mock_settings,
    )

    return mock_settings


@pytest.fixture
def redis_client(monkeypatch):
    mock_redis = MagicMock()

    monkeypatch.setattr(
        factory,
        "get_rewrite_redis_client",
        lambda: mock_redis,
    )

    return mock_redis


@pytest.fixture(autouse=True)
def clear_factory_caches():
    factories = [
        factory.get_rewrite_admission_controller,
        factory.get_rewrite_circuit_breaker,
        factory.get_rewrite_groq_client,
        factory.get_rewrite_cloudflare_client,
        factory.get_rewrite_provider,
    ]

    for item in factories:
        item.cache_clear()

    yield

    for item in factories:
        item.cache_clear()


# --------------------------------------------------
# Existing Redis infrastructure tests
# --------------------------------------------------

def test_admission_controller_uses_shared_redis_client(
    settings,
    redis_client,
):
    controller = factory.get_rewrite_admission_controller()

    assert controller._redis is redis_client


def test_circuit_breaker_uses_shared_redis_client(
    settings,
    redis_client,
):
    controller = factory.get_rewrite_circuit_breaker()

    assert controller._redis is redis_client


def test_both_controllers_share_same_redis_client(
    settings,
    redis_client,
):
    admission = factory.get_rewrite_admission_controller()
    circuit = factory.get_rewrite_circuit_breaker()

    assert admission._redis is circuit._redis
    assert admission._redis is redis_client


def test_admission_controller_receives_configuration(
    settings,
    redis_client,
):
    controller = factory.get_rewrite_admission_controller()

    assert controller._max_concurrency == 2
    assert controller._lease_ttl_ms == 90_000
    assert controller._key_ttl_ms == 95_000


def test_circuit_breaker_receives_configuration(
    settings,
    redis_client,
):
    controller = factory.get_rewrite_circuit_breaker()

    assert controller._failure_threshold == 3
    assert controller._recovery_ms == 30_000
    assert controller._probe_lease_ms == 90_000


# --------------------------------------------------
# Groq factory tests
# --------------------------------------------------

def test_groq_client_receives_correct_configuration(
    settings,
    monkeypatch,
):
    mock_client = MagicMock()

    constructor = MagicMock(return_value=mock_client)

    monkeypatch.setattr(
        factory,
        "RewriteGroqClient",
        constructor,
    )

    result = factory.get_rewrite_groq_client()

    assert result is mock_client

    constructor.assert_called_once_with(
        api_key=settings.rewrite_groq_api_key,
        timeout_seconds=80.0,
        read_timeout_seconds=30.0,
    )


def test_groq_client_is_cached(
    settings,
    monkeypatch,
):
    constructor = MagicMock()

    monkeypatch.setattr(
        factory,
        "RewriteGroqClient",
        constructor,
    )

    first = factory.get_rewrite_groq_client()
    second = factory.get_rewrite_groq_client()

    assert first is second
    constructor.assert_called_once()


# --------------------------------------------------
# Cloudflare factory tests
# --------------------------------------------------

def test_cloudflare_client_receives_correct_configuration(
    settings,
    monkeypatch,
):
    mock_client = MagicMock()

    constructor = MagicMock(return_value=mock_client)

    monkeypatch.setattr(
        factory,
        "RewriteCloudflareClient",
        constructor,
    )

    result = factory.get_rewrite_cloudflare_client()

    assert result is mock_client

    constructor.assert_called_once_with(
        account_id=settings.rewrite_cloudflare_account_id,
        api_token=settings.rewrite_cloudflare_api_token,
        timeout_seconds=80.0,
    )


def test_cloudflare_client_is_cached(
    settings,
    monkeypatch,
):
    constructor = MagicMock()

    monkeypatch.setattr(
        factory,
        "RewriteCloudflareClient",
        constructor,
    )

    first = factory.get_rewrite_cloudflare_client()
    second = factory.get_rewrite_cloudflare_client()

    assert first is second
    constructor.assert_called_once()


# --------------------------------------------------
# Provider factory tests
# --------------------------------------------------

def test_provider_receives_correct_dependencies(
    settings,
    monkeypatch,
):
    groq = MagicMock()
    cloudflare = MagicMock()
    admission = MagicMock()
    circuit = MagicMock()

    monkeypatch.setattr(
        factory,
        "get_rewrite_groq_client",
        lambda: groq,
    )

    monkeypatch.setattr(
        factory,
        "get_rewrite_cloudflare_client",
        lambda: cloudflare,
    )

    monkeypatch.setattr(
        factory,
        "get_rewrite_admission_controller",
        lambda: admission,
    )

    monkeypatch.setattr(
        factory,
        "get_rewrite_circuit_breaker",
        lambda: circuit,
    )

    constructor = MagicMock()

    monkeypatch.setattr(
        factory,
        "RewriteProvider",
        constructor,
    )

    factory.get_rewrite_provider()

    constructor.assert_called_once_with(
        groq_client=groq,
        cloudflare_client=cloudflare,
        admission_controller=admission,
        circuit_breaker=circuit,
        deadline_seconds=75.0,
    )


def test_provider_is_cached(
    settings,
    monkeypatch,
):
    constructor = MagicMock()

    monkeypatch.setattr(
        factory,
        "RewriteProvider",
        constructor,
    )

    first = factory.get_rewrite_provider()
    second = factory.get_rewrite_provider()

    assert first is second
    constructor.assert_called_once()


# --------------------------------------------------
# Existing caching tests
# --------------------------------------------------

def test_admission_controller_is_cached(
    settings,
    redis_client,
):
    first = factory.get_rewrite_admission_controller()
    second = factory.get_rewrite_admission_controller()

    assert first is second


def test_circuit_breaker_is_cached(
    settings,
    redis_client,
):
    first = factory.get_rewrite_circuit_breaker()
    second = factory.get_rewrite_circuit_breaker()

    assert first is second