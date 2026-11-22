from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr
from redis import Redis

from app.services.rewrite.redis_client import (
    RewriteRedisConfigurationError,
    create_rewrite_redis_client,
)


def test_redis_client_requires_configured_url():

    with pytest.raises(RewriteRedisConfigurationError):
        create_rewrite_redis_client(
            SecretStr("")
        )


def test_redis_client_requires_tls():

    with pytest.raises(RewriteRedisConfigurationError):
        create_rewrite_redis_client(
            SecretStr("redis://localhost:6379")
        )


def test_redis_client_uses_secure_connection_options(
    monkeypatch,
):

    mock_client = MagicMock(spec=Redis)

    def fake_from_url(url, **kwargs):
        assert url == "rediss://test:dummy@localhost:6379"

        assert kwargs["decode_responses"] is True
        assert kwargs["socket_connect_timeout"] == 5.0
        assert kwargs["socket_timeout"] == 5.0
        assert kwargs["retry_on_timeout"] is False
        assert kwargs["health_check_interval"] == 30

        return mock_client

    monkeypatch.setattr(
        Redis,
        "from_url",
        fake_from_url,
    )

    client = create_rewrite_redis_client(
        SecretStr(
            "rediss://test:dummy@localhost:6379"
        )
    )

    assert client is mock_client


def test_invalid_redis_url_does_not_expose_credentials(
    monkeypatch,
):

    def fake_from_url(url, **kwargs):
        raise ValueError(
            "Invalid URL containing sensitive information"
        )

    monkeypatch.setattr(
        Redis,
        "from_url",
        fake_from_url,
    )

    with pytest.raises(
        RewriteRedisConfigurationError
    ) as exc_info:

        create_rewrite_redis_client(
            SecretStr(
                "rediss://secret:password@example.com"
            )
        )

    assert "secret" not in str(exc_info.value)
    assert "password" not in str(exc_info.value)