"""Exceptions for the extraction service."""
from __future__ import annotations


class ExtractionError(Exception):
    """Base class for all extraction-related errors."""


class InvalidURLError(ExtractionError):
    """The submitted URL is structurally invalid or uses a disallowed scheme."""


class SSRFBlockedError(ExtractionError):
    """
    The URL (or a redirect target) resolves to, or points at, a network
    location that is disallowed for outbound requests (private/internal
    network, loopback, link-local, multicast, reserved, or a known cloud
    metadata endpoint).
    """


class FetchTimeoutError(ExtractionError):
    """The remote server did not respond within the configured timeout."""


class FetchConnectionError(ExtractionError):
    """A network-level error occurred while fetching the URL."""


class UnsupportedContentTypeError(ExtractionError):
    """The remote server returned a content-type we do not parse."""


class ResponseTooLargeError(ExtractionError):
    """The remote response exceeded the configured maximum size."""


class TooManyRedirectsError(ExtractionError):
    """The remote server issued more redirects than allowed."""


class InsufficientContentError(ExtractionError):
    """The page was fetched successfully but no meaningful content was extracted."""
