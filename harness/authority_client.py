"""Harness-side client for the bounded internal Authority protocol."""

from __future__ import annotations

import http.client
import json
import ssl
from typing import Any, Protocol, cast

from authority.protocol import (
    MintRequest,
    MintResponse,
    ResolutionRequest,
    ResolutionResponse,
)


class AuthorityClientError(RuntimeError):
    """The internal authority transport was unavailable or malformed."""


class AuthorityClient(Protocol):
    def resolve(self, request: ResolutionRequest) -> ResolutionResponse:
        """Perform call one."""
        ...

    def mint(self, request: MintRequest) -> MintResponse:
        """Perform call two."""
        ...


class InProcessAuthorityClient:
    """Explicit test composition seam; it does not bypass Token Service checks."""

    def __init__(self, service: Any, *, peer_identity: str = "harness-api") -> None:
        self._service = service
        self._peer_identity = peer_identity

    def resolve(self, request: ResolutionRequest) -> ResolutionResponse:
        return cast(
            ResolutionResponse,
            self._service.resolve(request, peer_identity=self._peer_identity),
        )

    def mint(self, request: MintRequest) -> MintResponse:
        return cast(
            MintResponse,
            self._service.mint(request, peer_identity=self._peer_identity),
        )


class MtlsAuthorityClient:
    """Standard-library HTTPS client for both internal authority routes."""

    def __init__(
        self,
        host: str,
        port: int,
        context: ssl.SSLContext,
        *,
        server_hostname: str = "localhost",
        timeout: float = 2.0,
    ) -> None:
        self._host = host
        self._port = port
        self._context = context
        self._server_hostname = server_hostname
        self._timeout = timeout
        self.raw_requests: list[str] = []

    def resolve(self, request: ResolutionRequest) -> ResolutionResponse:
        response = self._post("/internal/authority/v1/surface-resolution", request.to_dict())
        return ResolutionResponse.from_dict(response)

    def mint(self, request: MintRequest) -> MintResponse:
        response = self._post("/internal/authority/v1/run-capability-mint", request.to_dict())
        return MintResponse.from_dict(response)

    def _post(self, path: str, value: dict[str, object]) -> dict[str, object]:
        credential = value.get("graft_surface_credential")
        if not isinstance(credential, str):
            raise AuthorityClientError("request credential is malformed")
        self.raw_requests.append(credential)
        body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        connection = http.client.HTTPSConnection(
            self._host,
            self._port,
            context=self._context,
            timeout=self._timeout,
        )
        try:
            connection.request(
                "POST",
                path,
                body=body,
                headers={"Content-Type": "application/json", "Content-Length": str(len(body))},
            )
            response = connection.getresponse()
            raw = response.read()
            if response.status != 200:
                raise AuthorityClientError(f"authority HTTP status {response.status}")
            parsed = json.loads(raw.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise AuthorityClientError("authority response is not an object")
            return parsed
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise AuthorityClientError("authority transport failure") from exc
        finally:
            connection.close()
