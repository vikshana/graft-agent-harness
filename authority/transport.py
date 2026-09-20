"""Standard-library loopback mTLS HTTP adapter for the authority slice."""

from __future__ import annotations

import json
import socket
import ssl
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast

from .protocol import AuthorityProtocolError, MintRequest, ResolutionRequest
from .service import TestOnlyOpaqueTokenService


class _AuthorityHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        handler: type[BaseHTTPRequestHandler],
        service: TestOnlyOpaqueTokenService,
        peer_identity: str,
    ) -> None:
        super().__init__(address, handler)
        self.authority_service = service
        self.peer_identity = peer_identity


class _AuthorityHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        # Never log request headers or bodies: they may contain raw credentials.
        del format, args

    def do_POST(self) -> None:
        server = cast(_AuthorityHTTPServer, self.server)
        if self.path not in {
            "/internal/authority/v1/surface-resolution",
            "/internal/authority/v1/run-capability-mint",
        }:
            self._write_json(HTTPStatus.NOT_FOUND, {"graft_error": "not_found"})
            return
        if self.headers.get("Authorization") or self.headers.get("Cookie"):
            self._write_json(HTTPStatus.FORBIDDEN, {"graft_error": "transport_fallback_forbidden"})
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if length < 0 or length > 1024 * 1024:
                raise AuthorityProtocolError("invalid request body")
            raw = self.rfile.read(length)
            value = json.loads(raw.decode("utf-8"))
            if self.path.endswith("surface-resolution"):
                resolution_request = ResolutionRequest.from_dict(value)
                response = server.authority_service.resolve(
                    resolution_request,
                    peer_identity=self._peer_identity(server),
                ).to_dict()
            else:
                mint_request = MintRequest.from_dict(value)
                response = server.authority_service.mint(
                    mint_request,
                    peer_identity=self._peer_identity(server),
                ).to_dict()
            self._write_json(HTTPStatus.OK, response)
        except (AuthorityProtocolError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            self._write_json(HTTPStatus.BAD_REQUEST, {"graft_error": "contract_violation"})

    def _peer_identity(self, server: _AuthorityHTTPServer) -> str:
        del server
        certificate = self.connection.getpeercert()
        for subject_part in certificate.get("subject", ()):
            for key, value in subject_part:
                if key == "commonName" and isinstance(value, str):
                    return value
        return "unknown-peer"

    def _write_json(self, status: HTTPStatus, value: dict[str, Any]) -> None:
        payload = json.dumps(value, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)


class AuthorityIntegrationServer:
    """A real TLS-wrapped loopback server used only by integration tests."""

    def __init__(
        self,
        service: TestOnlyOpaqueTokenService,
        *,
        certificate_file: str,
        private_key_file: str,
        trust_bundle_file: str,
        peer_identity: str = "harness-api",
    ) -> None:
        self._service = service
        self._certificate_file = certificate_file
        self._private_key_file = private_key_file
        self._trust_bundle_file = trust_bundle_file
        self._peer_identity = peer_identity
        self._server: _AuthorityHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def address(self) -> tuple[str, int]:
        if self._server is None:
            raise RuntimeError("authority server is not running")
        address = self._server.server_address
        if not isinstance(address, tuple) or len(address) < 2:
            raise RuntimeError("unexpected loopback address")
        host, port = address[0], address[1]
        return str(host), int(port)

    def start(self) -> None:
        if self._server is not None:
            raise RuntimeError("authority server is already running")
        server = _AuthorityHTTPServer(
            ("127.0.0.1", 0), _AuthorityHandler, self._service, self._peer_identity
        )
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_cert_chain(self._certificate_file, self._private_key_file)
        context.load_verify_locations(cafile=self._trust_bundle_file)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        self._server = server
        self._thread = threading.Thread(
            target=server.serve_forever, name="authority-mtls", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        server = self._server
        thread = self._thread
        self._server = None
        self._thread = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=2)

    def __enter__(self) -> AuthorityIntegrationServer:
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        del args
        self.stop()


def create_mtls_client_context(
    *,
    ca_file: str,
    certificate_file: str,
    private_key_file: str,
) -> ssl.SSLContext:
    """Create a strict client context with no bearer/plain-HTTP fallback."""

    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_file)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = True
    context.load_cert_chain(certificate_file, private_key_file)
    return context


def open_mtls_connection(
    host: str,
    port: int,
    context: ssl.SSLContext,
    *,
    server_hostname: str = "localhost",
) -> ssl.SSLSocket:
    """Open a verified mTLS socket; useful for transport-negative tests."""

    raw = socket.create_connection((host, port), timeout=2)
    try:
        return context.wrap_socket(raw, server_hostname=server_hostname)
    except BaseException:
        raw.close()
        raise
