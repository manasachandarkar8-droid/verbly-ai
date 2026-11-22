"""
Safe HTTP fetching for Feature 1 (web scraping & content extraction).

SSRF hardening summary
-----------------------
For every hop (the original URL and every redirect target):

1. ``url_safety.validate_url_structure`` checks scheme/hostname shape and
   rejects embedded credentials / disallowed schemes / literal blocked
   hostnames.
2. ``url_safety.resolve_and_validate_host`` performs DNS resolution for
   that hostname *once* and validates every address it returned against
   the SSRF blocklist (loopback, private, link-local, multicast, reserved,
   known cloud metadata endpoints, IPv4-in-IPv6 tricks).
3. The outbound request is then rewritten to connect directly to the
   single validated, literal IP address from step 2, instead of the
   hostname. Because the request's URL already carries a literal IP,
   httpx/httpcore's connection pool will not perform any DNS resolution of
   its own when opening the socket -- there is no second lookup for an
   attacker's DNS server to answer differently. The original hostname is
   preserved in the ``Host`` header and as the TLS ``sni_hostname``
   extension, so the request and certificate validation are otherwise
   unaffected.
4. Redirects are handled manually (``follow_redirects=False`` + our own
   loop), so every hop re-runs steps 1-3 against the ``Location`` target
   before it is ever requested.

This closes the specific gap of "we validated the hostname, but the HTTP
client resolved it again on its own and got a different, unsafe answer."
See ``url_safety.py`` for the honest statement of what this does *not*
guarantee (it is an application-level resolve-once-and-pin, not a
sandboxed network namespace or infrastructure-level egress control).
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from app.core.config import get_settings
settings = get_settings()
from app.services.extraction.exceptions import (
    FetchConnectionError,
    FetchTimeoutError,
    ResponseTooLargeError,
    TooManyRedirectsError,
    UnsupportedContentTypeError,
)
from app.services.extraction.url_safety import (
    SafeHost,
    resolve_and_validate_host,
    validate_url_structure,
)

_REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}


@dataclass(frozen=True)
class FetchResult:
    url: str
    final_url: str
    status_code: int
    content_type: str
    html: str


def _build_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    timeout = httpx.Timeout(
        timeout=settings.fetch_timeout_seconds,
        connect=settings.fetch_connect_timeout_seconds,
    )
    return httpx.Client(
        transport=transport,
        timeout=timeout,
        follow_redirects=False,  # we validate + follow redirects ourselves
        headers={"User-Agent": settings.user_agent},
    )


def _pin_request_to_validated_ip(request: httpx.Request, hostname: str, safe_host: SafeHost) -> None:
    """
    Rewrite ``request`` in place so the connection targets the literal,
    already-validated IP address rather than the hostname, while keeping
    the Host header and TLS SNI hostname as the original name.
    """
    pinned_host = f"[{safe_host.ip}]" if safe_host.is_ipv6 else safe_host.ip
    request.url = request.url.copy_with(host=pinned_host)
    request.headers["host"] = hostname
    request.extensions = {**request.extensions, "sni_hostname": hostname}


def _read_limited_body(response: httpx.Response) -> str:
    limit = settings.max_response_bytes
    total = 0
    chunks: list[bytes] = []
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > limit:
            response.close()
            raise ResponseTooLargeError(
                f"Response exceeded the maximum allowed size of {limit} bytes."
            )
        chunks.append(chunk)
    raw = b"".join(chunks)
    encoding = response.encoding or "utf-8"
    try:
        return raw.decode(encoding, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def fetch_html(url: str, *, _transport: httpx.BaseTransport | None = None) -> FetchResult:
    """
    Fetch ``url`` and return its HTML body, enforcing SSRF protection,
    content-type restrictions, size limits, and manual redirect validation.

    ``_transport`` is an internal test seam (e.g. ``httpx.MockTransport``)
    that lets tests exercise the full validation/redirect pipeline without
    making real network calls. Production code should never pass it; the
    default (``None``) uses httpx's real network transport.
    """
    original_url = url
    validate_url_structure(url)

    current_url = url
    redirect_count = 0

    with _build_client(transport=_transport) as client:
        while True:
            parts = validate_url_structure(current_url)
            hostname = parts.hostname
            port = parts.port or (443 if parts.scheme == "https" else 80)

            # Resolve + validate DNS exactly once for this hop, then pin
            # the connection to that specific validated IP (see module
            # docstring). resolve_and_validate_host raises SSRFBlockedError
            # for any disallowed destination.
            safe_host = resolve_and_validate_host(hostname, port=port)

            request = client.build_request("GET", current_url)
            _pin_request_to_validated_ip(request, hostname, safe_host)

            try:
                response = client.send(request, stream=True)
            except httpx.TimeoutException as exc:
                raise FetchTimeoutError(f"Timed out fetching '{current_url}'.") from exc
            except httpx.HTTPError as exc:
                raise FetchConnectionError(
                    f"Network error fetching '{current_url}': {exc}"
                ) from exc

            if response.status_code in _REDIRECT_STATUS_CODES:
                response.close()
                location = response.headers.get("location")
                if not location:
                    raise FetchConnectionError(
                        f"Redirect response from '{current_url}' had no Location header."
                    )
                redirect_count += 1
                if redirect_count > settings.max_redirects:
                    raise TooManyRedirectsError(
                        f"Exceeded maximum of {settings.max_redirects} redirects."
                    )
                next_url = urljoin(current_url, location)
                # Structural re-validation now; full DNS re-validation
                # happens automatically at the top of the next loop
                # iteration before the redirect target is ever requested.
                validate_url_structure(next_url)
                current_url = next_url
                continue

            content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
            if content_type not in settings.allowed_content_types:
                response.close()
                raise UnsupportedContentTypeError(
                    f"Unsupported content type '{content_type or 'unknown'}'."
                )

            content_length = response.headers.get("content-length")
            if content_length is not None:
                try:
                    if int(content_length) > settings.max_response_bytes:
                        response.close()
                        raise ResponseTooLargeError(
                            f"Response exceeded the maximum allowed size of "
                            f"{settings.max_response_bytes} bytes."
                        )
                except ValueError:
                    pass  # malformed header; fall through to streamed enforcement

            html = _read_limited_body(response)
            # NOTE: response.url would report the pinned literal IP we
            # rewrote the request to, not the original hostname -- use our
            # own tracked, validated URL for the user-facing "final_url".
            final_url = current_url
            status_code = response.status_code
            response.close()

            return FetchResult(
                url=original_url,
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
                html=html,
            )
