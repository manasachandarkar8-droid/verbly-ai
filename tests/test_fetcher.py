"""
Fetcher tests. All network I/O is replaced with httpx.MockTransport and all
DNS resolution is mocked via socket.getaddrinfo -- no real network calls.
"""
from __future__ import annotations

import socket

import httpx
import pytest

from app.core.config import settings
from app.services.extraction.exceptions import (
    FetchTimeoutError,
    ResponseTooLargeError,
    SSRFBlockedError,
    TooManyRedirectsError,
    UnsupportedContentTypeError,
)
from app.services.extraction.fetcher import fetch_html


def _fake_addrinfo(ip: str):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    sockaddr = (ip, 443, 0, 0) if family == socket.AF_INET6 else (ip, 443)
    return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr)]


@pytest.fixture(autouse=True)
def _default_public_dns(monkeypatch):
    """By default, every hostname resolves to one fixed public IP."""
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda host, *a, **k: _fake_addrinfo("93.184.216.34")
    )


# ---------------------------------------------------------------------------
# Happy path + request pinning
# ---------------------------------------------------------------------------


def test_fetch_html_success_and_request_is_pinned_to_resolved_ip():
    seen_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=b"<html><body><p>hello world</p></body></html>",
        )

    result = fetch_html("https://example.com/page", _transport=httpx.MockTransport(handler))

    assert result.status_code == 200
    assert "hello world" in result.html
    assert result.final_url == "https://example.com/page"

    assert len(seen_requests) == 1
    sent = seen_requests[0]
    # The connection target must be the *resolved, validated* literal IP...
    assert sent.url.host == "93.184.216.34"
    # ...while the Host header and SNI hostname stay the original hostname.
    assert sent.headers["host"] == "example.com"
    assert sent.extensions.get("sni_hostname") == "example.com"


def test_fetch_html_uses_configured_user_agent():
    seen_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"<html><body><p>content long enough to pass the minimum</p></body></html>",
        )

    fetch_html("https://example.com/", _transport=httpx.MockTransport(handler))

    assert seen_requests[0].headers["user-agent"] == settings.user_agent
    assert settings.user_agent == "VerblyAI/1.0"
    assert "verbly.ai/bot" not in settings.user_agent


# ---------------------------------------------------------------------------
# Redirect handling: every hop must be re-validated
# ---------------------------------------------------------------------------


def test_redirect_to_public_host_is_followed():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers["host"] == "example.com":
            return httpx.Response(302, headers={"location": "https://safe-target.example/final"})
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"<html><body><p>final destination content here</p></body></html>",
        )

    result = fetch_html("https://example.com/start", _transport=httpx.MockTransport(handler))
    assert result.final_url == "https://safe-target.example/final"
    assert "final destination" in result.html


def test_redirect_to_ssrf_blocked_target_is_rejected(monkeypatch):
    def fake_getaddrinfo(host, *a, **k):
        if host == "internal.attacker.example":
            return _fake_addrinfo("169.254.169.254")
        return _fake_addrinfo("93.184.216.34")

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302, headers={"location": "http://internal.attacker.example/steal"}
        )

    with pytest.raises(SSRFBlockedError):
        fetch_html("https://example.com/start", _transport=httpx.MockTransport(handler))


def test_redirect_to_blocked_literal_ip_is_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})

    with pytest.raises(SSRFBlockedError):
        fetch_html("https://example.com/start", _transport=httpx.MockTransport(handler))


def test_too_many_redirects_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://example.com/next"})

    with pytest.raises(TooManyRedirectsError):
        fetch_html("https://example.com/start", _transport=httpx.MockTransport(handler))


# ---------------------------------------------------------------------------
# Content-type / size limits / timeouts
# ---------------------------------------------------------------------------


def test_unsupported_content_type_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/json"}, content=b"{}")

    with pytest.raises(UnsupportedContentTypeError):
        fetch_html("https://example.com/data.json", _transport=httpx.MockTransport(handler))


def test_oversized_response_rejected(monkeypatch):
    monkeypatch.setattr(settings, "max_response_bytes", 10)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"<html>" + b"a" * 1000 + b"</html>",
        )

    with pytest.raises(ResponseTooLargeError):
        fetch_html("https://example.com/big", _transport=httpx.MockTransport(handler))


def test_timeout_raises_fetch_timeout_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    with pytest.raises(FetchTimeoutError):
        fetch_html("https://example.com/slow", _transport=httpx.MockTransport(handler))
