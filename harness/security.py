"""Run-scoped capability token reference implementation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class CapabilityDenied(PermissionError):
    """A capability token failed independent resource-server validation."""


@dataclass(frozen=True, slots=True)
class CapabilityClaims:
    graft_run_id: str
    graft_tenant_id: str
    tool_classes: frozenset[str]
    expires_at: int
    audience: str = "graft-tool-gateway"
    issuer: str = "graft-harness"


class CapabilityAuthority:
    def __init__(self, secret: bytes, clock: Callable[[], float] = time.time) -> None:
        self._secret = secret
        self._clock = clock

    def mint(self, claims: CapabilityClaims) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        body = {
            "graft_run_id": claims.graft_run_id,
            "graft_tenant_id": claims.graft_tenant_id,
            "tool_classes": sorted(claims.tool_classes),
            "exp": claims.expires_at,
            "aud": claims.audience,
            "iss": claims.issuer,
        }
        encoded_header = self._encode(header)
        encoded_body = self._encode(body)
        unsigned = f"{encoded_header}.{encoded_body}".encode()
        signature = self._sign(unsigned)
        return f"{encoded_header}.{encoded_body}.{signature}"

    def validate(
        self, token: str, *, graft_run_id: str, graft_tenant_id: str, required_tool_class: str
    ) -> CapabilityClaims:
        try:
            encoded_header, encoded_body, signature = token.split(".")
            unsigned = f"{encoded_header}.{encoded_body}".encode()
            expected = self._sign(unsigned)
            if not hmac.compare_digest(signature, expected):
                raise CapabilityDenied("invalid capability signature")
            header = json.loads(self._decode(encoded_header))
            body: dict[str, Any] = json.loads(self._decode(encoded_body))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise CapabilityDenied("malformed capability token") from exc
        if header.get("alg") != "HS256":
            raise CapabilityDenied("unsupported capability algorithm")
        if body.get("aud") != "graft-tool-gateway" or body.get("iss") != "graft-harness":
            raise CapabilityDenied("invalid capability audience or issuer")
        if int(body.get("exp", 0)) <= int(self._clock()):
            raise CapabilityDenied("expired capability token")
        if (
            body.get("graft_run_id") != graft_run_id
            or body.get("graft_tenant_id") != graft_tenant_id
        ):
            raise CapabilityDenied("capability binding mismatch")
        tool_classes = frozenset(body.get("tool_classes", []))
        if required_tool_class not in tool_classes:
            raise CapabilityDenied("ToolClass is not authorised")
        return CapabilityClaims(graft_run_id, graft_tenant_id, tool_classes, int(body["exp"]))

    def _sign(self, value: bytes) -> str:
        return self._encode_bytes(hmac.new(self._secret, value, hashlib.sha256).digest())

    @staticmethod
    def _encode(value: object) -> str:
        return CapabilityAuthority._encode_bytes(
            json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
        )

    @staticmethod
    def _encode_bytes(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

    @staticmethod
    def _decode(value: str) -> str:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()
