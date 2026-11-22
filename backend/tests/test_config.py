from __future__ import annotations

import importlib

from app.core.config import Settings, settings


def test_default_user_agent_is_neutral_and_configurable():
    assert settings.user_agent == "VerblyAI/1.0"
    # Regression guard for the corrected User-Agent: must not reference the
    # previously-used, unpublished /bot URL.
    assert "verbly.ai/bot" not in settings.user_agent
    assert "http://" not in settings.user_agent
    assert "https://" not in settings.user_agent


def test_user_agent_is_configurable_via_environment(monkeypatch):
    monkeypatch.setenv("VERBLY_USER_AGENT", "CustomAgent/9.9")
    reloaded = Settings()
    assert reloaded.user_agent == "CustomAgent/9.9"


def test_settings_module_importable():
    # Sanity/foundation check that config wiring itself is intact.
    module = importlib.import_module("app.core.config")
    assert hasattr(module, "settings")


def test_feature_6_credentials_are_loaded_independently(monkeypatch):
    monkeypatch.setenv(
        "VERBLY_GROQ_API_KEY",
        "feature5-groq-test-key",
    )
    monkeypatch.setenv(
        "VERBLY_REWRITE_GROQ_API_KEY",
        "feature6-groq-test-key",
    )

    monkeypatch.setenv(
        "VERBLY_CLOUDFLARE_ACCOUNT_ID",
        "feature5-account",
    )
    monkeypatch.setenv(
        "VERBLY_REWRITE_CLOUDFLARE_ACCOUNT_ID",
        "feature6-account",
    )

    monkeypatch.setenv(
        "VERBLY_CLOUDFLARE_API_TOKEN",
        "feature5-cloudflare-token",
    )
    monkeypatch.setenv(
        "VERBLY_REWRITE_CLOUDFLARE_API_TOKEN",
        "feature6-cloudflare-token",
    )

    config = Settings(_env_file=None)

    assert (
        config.groq_api_key.get_secret_value()
        == "feature5-groq-test-key"
    )
    assert (
        config.rewrite_groq_api_key.get_secret_value()
        == "feature6-groq-test-key"
    )

    assert config.cloudflare_account_id == "feature5-account"
    assert config.rewrite_cloudflare_account_id == "feature6-account"

    assert (
        config.cloudflare_api_token.get_secret_value()
        == "feature5-cloudflare-token"
    )
    assert (
        config.rewrite_cloudflare_api_token.get_secret_value()
        == "feature6-cloudflare-token"
    )


def test_feature_6_provider_timeout_default():
    config = Settings(_env_file=None)

    assert config.rewrite_provider_timeout_seconds == 80.0