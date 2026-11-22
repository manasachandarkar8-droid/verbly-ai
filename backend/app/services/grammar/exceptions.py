from __future__ import annotations

class GrammarEngineError(Exception):
    """Base error for failures communicating with the grammar engine."""

class GrammarEngineUnavailableError(GrammarEngineError):
    """LanguageTool could not be reached."""

class GrammarEngineTimeoutError(GrammarEngineError):
    """LanguageTool did not respond within the configured timeout."""

class GrammarEngineResponseError(GrammarEngineError):
    """LanguageTool returned an invalid or unsuccessful response."""
