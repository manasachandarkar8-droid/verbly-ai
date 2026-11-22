from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.services.grammar.constants import LANGUAGETOOL_CHECK_PATH, LANGUAGETOOL_LANGUAGE
from app.services.grammar.exceptions import (
    GrammarEngineResponseError,
    GrammarEngineTimeoutError,
    GrammarEngineUnavailableError,
)

@dataclass(frozen=True)
class LanguageToolCheckResult:
    matches: list[dict[str, Any]]


def _build_client(transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
    timeout = httpx.Timeout(
        timeout=settings.grammar_languagetool_timeout_seconds,
        connect=settings.grammar_languagetool_connect_timeout_seconds,
    )
    return httpx.AsyncClient(
        base_url=settings.grammar_languagetool_base_url,
        timeout=timeout,
        transport=transport,
    )


async def check_text(
    text: str,
    _transport: httpx.AsyncBaseTransport | None = None,
) -> LanguageToolCheckResult:
    try:
        async with _build_client(transport=_transport) as client:
            response = await client.post(
                LANGUAGETOOL_CHECK_PATH,
                data={"text": text, "language": LANGUAGETOOL_LANGUAGE},
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise GrammarEngineTimeoutError("LanguageTool request timed out.") from exc
    except httpx.HTTPStatusError as exc:
        raise GrammarEngineResponseError(
            f"LanguageTool returned HTTP {exc.response.status_code}."
        ) from exc
    except httpx.HTTPError as exc:
        raise GrammarEngineUnavailableError("LanguageTool is unavailable.") from exc

    try:
        payload = response.json()
    except (ValueError, TypeError) as exc:
        raise GrammarEngineResponseError("LanguageTool returned malformed JSON.") from exc

    if not isinstance(payload, dict):
        raise GrammarEngineResponseError("LanguageTool response must be a JSON object.")
    matches = payload.get("matches")
    if not isinstance(matches, list):
        raise GrammarEngineResponseError("LanguageTool response is missing a matches list.")
    return LanguageToolCheckResult(matches=matches)
