"""
Empirical verification of the exact httpx/httpcore mechanism fetcher.py
relies on: that pinning a request's connection target to a literal IP
while setting Host header + `sni_hostname` extension to the *original*
hostname results in:

  1. the TCP connection going to the literal IP (proved by using a
     hostname that isn't resolvable via DNS at all -- the request would
     fail outright if httpx/httpcore tried to resolve it),
  2. the TLS ClientHello SNI carrying the original hostname, and
  3. certificate hostname verification being enforced against that same
     original hostname (a mismatched cert is rejected; a matching cert is
     accepted).

This talks to a real TLS socket on 127.0.0.1 (loopback only, no external
network, no real DNS). It intentionally does NOT go through
app.services.extraction.url_safety's SSRF blocklist -- 127.0.0.1 would
normally (and correctly) be rejected by that policy. The point here is to
verify the low-level connection-pinning primitive itself, which is also
exactly what fetcher.py's `_pin_request_to_validated_ip` does after
url_safety has already approved a destination.

If a future httpx/httpcore upgrade changes this behavior, this test will
fail loudly instead of the assumption silently going stale.
"""
from __future__ import annotations

import http.server
import shutil
import ssl
import subprocess
import threading

import httpx
import pytest

CORRECT_HOSTNAME = "pinned.testhost.internal"  # deliberately not in real DNS
WRONG_HOSTNAME = "totally-different-name.example"

pytestmark = pytest.mark.skipif(
    shutil.which("openssl") is None, reason="openssl binary not available to generate a test cert"
)


@pytest.fixture()
def cert_and_key(tmp_path):
    cert = tmp_path / "server.crt"
    key = tmp_path / "server.key"
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(key), "-out", str(cert), "-days", "2",
            "-subj", f"/CN={CORRECT_HOSTNAME}",
            "-addext", f"subjectAltName=DNS:{CORRECT_HOSTNAME}",
        ],
        check=True,
        capture_output=True,
    )
    return str(cert), str(key)


@pytest.fixture()
def local_tls_server(cert_and_key):
    cert, key = cert_and_key
    received_sni = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = f"host_header={self.headers.get('Host')};sni={received_sni.get('last')}".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    def sni_callback(_ssl_socket, server_name, _ssl_context):
        received_sni["last"] = server_name

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    ctx.sni_callback = sni_callback

    httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield port, cert
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def _pinned_request(port: int, cert: str, sni_hostname: str) -> httpx.Response:
    """Reproduces exactly what fetcher.py's _pin_request_to_validated_ip does."""
    ssl_context = ssl.create_default_context(cafile=cert)
    client = httpx.Client(verify=ssl_context)
    try:
        request = client.build_request("GET", f"https://{sni_hostname}:{port}/")
        request.url = request.url.copy_with(host="127.0.0.1")  # pin to literal IP
        request.headers["host"] = sni_hostname
        request.extensions = {**request.extensions, "sni_hostname": sni_hostname}
        return client.send(request)
    finally:
        client.close()


def test_pinned_connection_uses_original_hostname_for_sni_and_cert_verification(local_tls_server):
    port, cert = local_tls_server

    response = _pinned_request(port, cert, CORRECT_HOSTNAME)
    assert response.status_code == 200
    body = response.text
    # The connection succeeded even though CORRECT_HOSTNAME is not resolvable
    # via real DNS -- proving the connection went to the pinned literal IP,
    # not to a fresh resolution of the hostname.
    assert f"sni={CORRECT_HOSTNAME}" in body
    assert f"host_header={CORRECT_HOSTNAME}" in body


def test_pinned_connection_rejects_mismatched_certificate_hostname(local_tls_server):
    port, cert = local_tls_server

    with pytest.raises(httpx.ConnectError):
        _pinned_request(port, cert, WRONG_HOSTNAME)
