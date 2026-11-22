from functools import lru_cache

from app.core.config import get_settings

from app.services.ai.groq_client import GroqClient
from app.services.ai.cloudflare_client import CloudflareClient
from app.services.ai.provider import AIProvider


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    """Return the shared AI provider with lazy client initialization."""

    settings = get_settings()

    return AIProvider(
        groq_client_factory=lambda: GroqClient(
            api_key=settings.groq_api_key,
            timeout_seconds=(
                settings.content_analysis_provider_timeout_seconds
            ),
        ),
        cloudflare_client_factory=lambda: CloudflareClient(
            account_id=settings.cloudflare_account_id,
            api_token=settings.cloudflare_api_token,
            timeout_seconds=(
                settings.content_analysis_provider_timeout_seconds
            ),
        ),
    )