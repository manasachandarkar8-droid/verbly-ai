"""
Application configuration (foundation layer).

Loaded via pydantic-settings so values can be overridden with environment
variables (see .env.example) without code changes.
"""
from __future__ import annotations
from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General / app-level -----------------------------------------------
    app_name: str = "Verbly AI Backend"
    environment: str = "development"
    debug: bool = False

    # --- CORS ---------------------------------------------------------------
    cors_allow_origins: list[str] = [
    "http://localhost:3000",
    "http://localhost:3002",
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # --- Database (foundation; not used by Feature 1) -----------------------
    database_url: str = "postgresql+psycopg://verbly:verbly@localhost:5432/verbly"

    # --- Feature 1: extraction / fetcher settings ---------------------------

    # NOTE: previously "VerblyBot/1.0 (+https://verbly.ai/bot)". That
    # referenced a URL we do not actually operate, which is misleading to
    # server operators reading the User-Agent string. Replaced with a
    # neutral, professional identifier. Still fully configurable via
    # VERBLY_USER_AGENT for deployments that want to point to a real,
    # published bot-info page later.
    user_agent: str = Field(
    default="VerblyAI/1.0",
    validation_alias=AliasChoices("VERBLY_USER_AGENT", "USER_AGENT"),
)

    fetch_timeout_seconds: float = 10.0
    fetch_connect_timeout_seconds: float = 5.0
    max_response_bytes: int = 5 * 1024 * 1024  # 5 MB
    max_redirects: int = 5

    allowed_content_types: tuple[str, ...] = (
        "text/html",
        "application/xhtml+xml",
    )

    # --- Feature 4: grammar / self-hosted LanguageTool settings --------------

    # --- Feature 4: grammar / self-hosted LanguageTool settings --------------

    grammar_languagetool_base_url: str = Field(
        default="http://languagetool:8010",
        validation_alias=AliasChoices(
            "VERBLY_LANGUAGETOOL_BASE_URL", "LANGUAGETOOL_BASE_URL"
        ),
    )

    grammar_languagetool_timeout_seconds: float = Field(
        default=15.0,
        validation_alias=AliasChoices(
            "VERBLY_LANGUAGETOOL_TIMEOUT_SECONDS", "LANGUAGETOOL_TIMEOUT_SECONDS"
        ),
    )

    grammar_languagetool_connect_timeout_seconds: float = Field(
        default=5.0,
        validation_alias=AliasChoices(
            "VERBLY_LANGUAGETOOL_CONNECT_TIMEOUT_SECONDS",
            "LANGUAGETOOL_CONNECT_TIMEOUT_SECONDS",
        ),
    )

        # --- Feature 5: AI/NLP content analysis -------------------------------

       # --- Feature 5: AI-powered content analysis -----------------------------

    # Primary provider: Groq
    groq_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices(
            "VERBLY_GROQ_API_KEY",
            "GROQ_API_KEY",
        ),
    )

    # Backup provider: Cloudflare Workers AI
    cloudflare_account_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "VERBLY_CLOUDFLARE_ACCOUNT_ID",
            "CLOUDFLARE_ACCOUNT_ID",
        ),
    )

    cloudflare_api_token: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices(
            "VERBLY_CLOUDFLARE_API_TOKEN",
            "CLOUDFLARE_API_TOKEN",
        ),
    )

    # Provider request timeout
    content_analysis_provider_timeout_seconds: float = Field(
        default=80.0,
        gt=0.0,
        le=120.0,
    )

    # Limit concurrent API-based analyses
    content_analysis_max_concurrency: int = Field(
        default=1,
        ge=1,
        le=2,
    )

    # Maximum time to wait for an available analysis slot
    content_analysis_busy_timeout_seconds: float = Field(
        default=10.0,
        ge=0.0,
        le=60.0,
    )

        # TEMPORARY: Legacy settings retained during Feature 5 migration.
    # Remove only after the API replacement is fully tested.

    content_analysis_model_dir: Path = Path("models")

    content_analysis_preload_models: bool = False

    content_analysis_deadline_seconds: float = Field(
        default=110.0,
        gt=0.0,
        le=120.0,
    )

    # --- Feature 6: AI Content Rewrite ---

    # Primary provider: Groq
    rewrite_groq_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices(
            "VERBLY_REWRITE_GROQ_API_KEY",
        ),
    )

    # Backup provider: Cloudflare Workers AI
    rewrite_cloudflare_account_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "VERBLY_REWRITE_CLOUDFLARE_ACCOUNT_ID",
        ),
    )

    rewrite_cloudflare_api_token: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices(
            "VERBLY_REWRITE_CLOUDFLARE_API_TOKEN",
        ),
    )

    rewrite_provider_timeout_seconds: float = Field(
        default=80.0,
        gt=0.0,
        le=120.0,
    )
        # Redis infrastructure: Feature 6
    rewrite_redis_url: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices(
            "VERBLY_REWRITE_REDIS_URL",
        ),
    )

        # Rewrite execution limits
    rewrite_deadline_seconds: float = Field(
        default=75.0,
        gt=0.0,
        le=120.0,
    )

    rewrite_groq_read_timeout_seconds: float = Field(
        default=30.0,
        gt=0.0,
        le=75.0,
    )

    # Distributed admission control
    rewrite_max_concurrency: int = Field(
        default=2,
        ge=1,
        le=2,
    )

    rewrite_lease_ttl_seconds: int = Field(
        default=90,
        ge=76,
        le=180,
    )

    # Provider circuit breakers
    rewrite_circuit_failure_threshold: int = Field(
        default=3,
        ge=1,
        le=10,
    )

    rewrite_circuit_recovery_seconds: float = Field(
        default=30.0,
        gt=0.0,
        le=300.0,
    )

settings = Settings()

def get_settings() -> Settings:
    return settings
