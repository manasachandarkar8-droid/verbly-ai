"""
Deterministic SSRF / DNS-resolution tests.

All DNS resolution is mocked via ``socket.getaddrinfo`` monkeypatching so
these tests never touch the real network or real DNS.
"""
from __future__ import annotations

import socket

import pytest

from app.services.extraction.exceptions import InvalidURLError, SSRFBlockedError
from app.services.extraction.url_safety import (
    resolve_and_validate_host,
    validate_url_structure,
)


def _fake_addrinfo(*ips: str):
    """Build a socket.getaddrinfo-shaped return value for the given IPs."""
    results = []
    for ip in ips:
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        sockaddr = (ip, 443, 0, 0) if family == socket.AF_INET6 else (ip, 443)
        results.append((family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr))
    return results


# ---------------------------------------------------------------------------
# Structural validation (no network)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/file",
        "file:///etc/passwd",
        "gopher://example.com",
        "javascript:alert(1)",
        "",
        "not a url",
        "https://",
    ],
)
def test_rejects_invalid_or_disallowed_scheme(url):
    with pytest.raises(InvalidURLError):
        validate_url_structure(url)


def test_rejects_embedded_credentials():
    with pytest.raises(InvalidURLError):
        validate_url_structure("https://user:pass@example.com/")


def test_rejects_localhost_hostname_literal():
    with pytest.raises(SSRFBlockedError):
        validate_url_structure("http://localhost/")


def test_accepts_well_formed_public_url():
    parts = validate_url_structure("https://example.com/articles/1")
    assert parts.hostname == "example.com"
    assert parts.scheme == "https"


# ---------------------------------------------------------------------------
# IP-category blocking (literal IPs, no DNS involved)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "literal_ip",
    [
        "127.0.0.1",  # loopback
        "127.0.0.53",  # loopback range
        "10.0.0.5",  # RFC1918 private
        "172.16.5.1",  # RFC1918 private
        "192.168.1.1",  # RFC1918 private
        "169.254.169.254",  # link-local / AWS-GCP-Azure metadata
        "169.254.1.1",  # link-local
        "224.0.0.1",  # multicast
        "0.0.0.0",  # unspecified
        "100.64.0.1",  # CGNAT / shared address space
        "100.100.100.200",  # Alibaba Cloud metadata
        "::1",  # IPv6 loopback
        "fe80::1",  # IPv6 link-local
        "fc00::1",  # IPv6 unique local (private)
        "fd00:ec2::254",  # AWS IMDSv2 IPv6
        "ff02::1",  # IPv6 multicast
        "::",  # IPv6 unspecified
        "::ffff:127.0.0.1",  # IPv4-mapped IPv6 loopback (smuggling attempt)
        "::ffff:10.0.0.1",  # IPv4-mapped IPv6 private (smuggling attempt)
    ],
)
def test_literal_blocked_ips_are_rejected(literal_ip, monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("DNS should not be consulted for a literal IP")
    ))
    with pytest.raises(SSRFBlockedError):
        resolve_and_validate_host(literal_ip, port=443)


@pytest.mark.parametrize("public_ip", ["93.184.216.34", "8.8.8.8", "2606:2800:220:1:248:1893:25c8:1946"])
def test_literal_public_ips_are_allowed(public_ip, monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("DNS should not be consulted for a literal IP")
    ))
    safe = resolve_and_validate_host(public_ip, port=443)
    assert safe.ip == public_ip


# ---------------------------------------------------------------------------
# Hostname resolution (mocked DNS) -- this is the DNS-rebinding surface
# ---------------------------------------------------------------------------


def test_hostname_resolving_to_public_ip_is_allowed(monkeypatch):
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *a, **k: _fake_addrinfo("93.184.216.34")
    )
    safe = resolve_and_validate_host("example.com", port=443)
    assert safe.ip == "93.184.216.34"
    assert safe.hostname == "example.com"
    assert safe.is_ipv6 is False


def test_hostname_resolving_to_private_ip_is_blocked(monkeypatch):
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *a, **k: _fake_addrinfo("10.0.0.5")
    )
    with pytest.raises(SSRFBlockedError):
        resolve_and_validate_host("internal.example.com", port=443)


def test_hostname_resolving_to_metadata_ip_is_blocked(monkeypatch):
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *a, **k: _fake_addrinfo("169.254.169.254")
    )
    with pytest.raises(SSRFBlockedError):
        resolve_and_validate_host("attacker-controlled.example", port=80)


def test_hostname_resolving_to_ipv6_loopback_is_blocked(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _fake_addrinfo("::1"))
    with pytest.raises(SSRFBlockedError):
        resolve_and_validate_host("evil.example", port=443)


def test_hostname_with_mixed_public_and_private_answers_is_rejected(monkeypatch):
    """
    Rebinding-style DNS answer: a resolver that returns *both* a public and
    a private address for the same name. We must not silently pick the
    'good' one -- the whole hostname is treated as unsafe. This is the
    core scenario that motivates resolving once and validating every
    returned address rather than trusting any single answer in isolation.
    """
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: _fake_addrinfo("93.184.216.34", "10.0.0.5"),
    )
    with pytest.raises(SSRFBlockedError):
        resolve_and_validate_host("rebinder.example", port=443)


def test_hostname_that_fails_to_resolve_is_blocked(monkeypatch):
    def _raise(*_a, **_k):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(socket, "getaddrinfo", _raise)
    with pytest.raises(SSRFBlockedError):
        resolve_and_validate_host("does-not-exist.invalid", port=443)


def test_resolution_happens_exactly_once_per_call(monkeypatch):
    """
    Guards against a regression where validation and connection logic each
    independently call the resolver -- which is exactly the shape of bug
    that enables DNS rebinding.
    """
    calls = {"count": 0}

    def _counting_getaddrinfo(*_a, **_k):
        calls["count"] += 1
        return _fake_addrinfo("93.184.216.34")

    monkeypatch.setattr(socket, "getaddrinfo", _counting_getaddrinfo)
    resolve_and_validate_host("example.com", port=443)
    assert calls["count"] == 1
