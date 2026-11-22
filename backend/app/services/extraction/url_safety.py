"""
URL / network-destination safety checks (SSRF protection).

SECURITY MODEL
---------------
Two things have to be true for a fetch to be safe:

1. The URL's hostname must not resolve to a disallowed IP address
   (loopback / private / link-local / multicast / reserved / known cloud
   metadata endpoint), for every hop including redirects.
2. The socket the HTTP client actually connects to must be the same IP
   address that was validated in step 1 -- not a second, independent DNS
   lookup performed later by the network stack.

(2) is the part that is easy to get wrong. If you validate
``socket.getaddrinfo(hostname)`` and then hand the *hostname* (not the IP)
to the HTTP client, the client will resolve the name again when it opens
the socket. An attacker controlling DNS for that name can return a public
IP for your validation lookup and a private/internal IP a few milliseconds
later for the client's own lookup ("DNS rebinding"). The validation would
pass and the request would still hit an internal host.

This module resolves each hostname exactly once, validates every address
that resolution returned, and hands back the literal IP that must be used
for the connection. ``fetcher.py`` pins the actual TCP connection to that
IP (see ``_PinnedDNSTransport``) instead of letting httpx/httpcore resolve
the hostname again. That closes the classic rebinding window for this
process.

HONEST LIMITATION
------------------
This is resolve-once-and-pin, not a kernel/socket-level guarantee. It
removes the specific "validate hostname, then let the transport do its own
independent DNS lookup" gap. It does **not** provide the kind of guarantee
you'd get from a sandboxed network namespace, an explicit egress allowlist
enforced by infrastructure (e.g. an egress proxy / firewall), or from a
DNS resolver you fully control end-to-end. Time-of-check-to-time-of-use is
reduced to "the single resolution we performed and then reused for the
connection" rather than eliminated as a general concept -- if the OS-level
resolver cache itself were compromised between our lookup and our own
subsequent connect *to the IP we already pinned*, that connect would still
go to the address we validated, because we no longer ask the resolver a
second time. The residual risk is therefore effectively closed for this
architecture; see the fetcher module docstring for the precise boundary.
"""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit

from app.services.extraction.exceptions import InvalidURLError, SSRFBlockedError

ALLOWED_SCHEMES = {"http", "https"}

# Explicit belt-and-suspenders list of known cloud / virtualization metadata
# endpoints. Most of these already fall under link-local or private ranges
# and would be blocked by the generic checks below; they are listed
# explicitly so the intent is documented and so the check survives even if
# a future Python ipaddress release narrows a generic category.
_BLOCKED_LITERAL_NETWORKS = [
    ipaddress.ip_network("169.254.169.254/32"),  # AWS/GCP/Azure/OCI metadata
    ipaddress.ip_network("169.254.170.2/32"),  # AWS ECS task metadata
    ipaddress.ip_network("100.100.100.200/32"),  # Alibaba Cloud metadata
    ipaddress.ip_network("192.0.0.192/32"),  # Oracle Cloud metadata (alt)
    ipaddress.ip_network("fd00:ec2::254/128"),  # AWS IMDSv2 (IPv6)
    # RFC 6598 Carrier-Grade NAT / shared address space. Not consistently
    # marked "private" across Python versions' ipaddress module, so it is
    # listed explicitly. Used internally by some cloud/CGNAT networks.
    ipaddress.ip_network("100.64.0.0/10"),
]

_BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain", "metadata", "metadata.google.internal"}


@dataclass(frozen=True)
class SafeHost:
    """A hostname together with the single validated, pinnable IP to use."""

    hostname: str
    ip: str
    is_ipv6: bool


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_loopback:
        return True
    if ip.is_private:  # covers RFC1918, RFC4193 (fc00::/7), CGNAT 100.64/10, etc.
        return True
    if ip.is_link_local:  # covers 169.254.0.0/16 and fe80::/10
        return True
    if ip.is_multicast:
        return True
    if ip.is_unspecified:  # 0.0.0.0 / ::
        return True
    if ip.is_reserved:
        return True
    # IPv4-mapped / IPv4-compatible IPv6 addresses ("::ffff:127.0.0.1" etc.)
    # can smuggle a blocked IPv4 address past naive IPv6-only checks.
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None and _is_blocked_ip(mapped):
        return True
    sixtofour = getattr(ip, "sixtofour", None)
    if sixtofour is not None and _is_blocked_ip(sixtofour):
        return True
    teredo = getattr(ip, "teredo", None)
    if teredo is not None:
        # teredo is a (server_ip, client_ip) tuple of embedded IPv4 addrs
        if any(_is_blocked_ip(addr) for addr in teredo):
            return True
    for network in _BLOCKED_LITERAL_NETWORKS:
        if ip in network:
            return True
    return False


def validate_url_structure(url: str) -> SplitResult:
    """Validate scheme/hostname shape only. Does not touch the network."""
    if not url or not isinstance(url, str):
        raise InvalidURLError("URL must be a non-empty string.")

    parts = urlsplit(url.strip())

    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise InvalidURLError(
            f"Unsupported URL scheme '{parts.scheme}'. Only http/https are allowed."
        )

    if not parts.hostname:
        raise InvalidURLError("URL must include a hostname.")

    if parts.username or parts.password:
        # Userinfo in URLs is a common SSRF/phishing trick and has no
        # legitimate use for this feature.
        raise InvalidURLError("URLs with embedded credentials are not allowed.")

    hostname = parts.hostname.lower().rstrip(".")
    if hostname in _BLOCKED_HOSTNAMES:
        raise SSRFBlockedError(f"Host '{hostname}' is not allowed.")

    return parts


def resolve_and_validate_host(hostname: str, *, port: int) -> SafeHost:
    """
    Resolve ``hostname`` exactly once and validate every address the
    resolver returned. Returns the single IP the caller must pin the
    outbound connection to.

    If the hostname resolves to a mix of safe and unsafe addresses, the
    whole hostname is rejected rather than silently picking a "good" one.
    A resolver that can be induced to answer with an internal address at
    all is not one we should trust to consistently answer safely -- that
    is precisely the rebinding scenario we're defending against, and
    picking-the-safe-answer would just move the race to "which answer
    does the client's own second lookup land on", the exact bug this
    module exists to avoid.
    """
    # A literal IP address as the hostname: no DNS involved.
    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        if _is_blocked_ip(literal_ip):
            raise SSRFBlockedError(f"IP address '{hostname}' is not allowed.")
        return SafeHost(hostname=hostname, ip=str(literal_ip), is_ipv6=literal_ip.version == 6)

    try:
        addrinfo = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise SSRFBlockedError(f"Could not resolve host '{hostname}': {exc}") from exc

    if not addrinfo:
        raise SSRFBlockedError(f"Host '{hostname}' did not resolve to any address.")

    resolved_ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for family, _type, _proto, _canonname, sockaddr in addrinfo:
        raw_ip = sockaddr[0]
        ip_obj = ipaddress.ip_address(raw_ip.split("%")[0])  # strip IPv6 zone id
        resolved_ips.append(ip_obj)

    blocked = [ip for ip in resolved_ips if _is_blocked_ip(ip)]
    if blocked:
        raise SSRFBlockedError(
            f"Host '{hostname}' resolves to a disallowed network address "
            f"({blocked[0]}). Refusing to fetch."
        )

    chosen = resolved_ips[0]
    return SafeHost(hostname=hostname, ip=str(chosen), is_ipv6=chosen.version == 6)
