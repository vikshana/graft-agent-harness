"""Deterministic Gate 1 authority doubles, with no production key material."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from .protocol import (
    MintRequest,
    MintResponse,
    ResolutionRequest,
    ResolutionResponse,
    VerifiedIdentity,
    canonical_webhook_fingerprint,
)


class SurfaceVerificationFailure(Exception):
    """Safe verifier failure; its message is never put in a wire response."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class SurfaceVerifier(Protocol):
    """The only identity input accepted by the Token Service."""

    revision: str

    def verify(
        self,
        *,
        surface: str,
        credential: str,
        webhook_envelope: dict[str, Any] | None,
        now: float,
    ) -> VerifiedIdentity:
        """Verify the exact raw credential and derive fresh authority."""
        raise NotImplementedError


class DeterministicSurfaceVerifier:
    """Configurable verifier double used by unit and transport tests.

    Credentials are dictionary keys only in this test double; the production
    verifier must resolve credentials without exposing or persisting them.
    The implementation compares strings exactly, including whitespace and
    Unicode, and never trims or normalises them.
    """

    def __init__(
        self,
        credentials: Mapping[tuple[str, str], VerifiedIdentity] | None = None,
        *,
        revision: str = "deterministic-test-v1",
        expired: set[tuple[str, str]] | None = None,
    ) -> None:
        self.revision = revision
        self._credentials = dict(credentials or {})
        self._expired = set(expired or set())
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def set_identity(self, surface: str, credential: str, identity: VerifiedIdentity) -> None:
        self._credentials[(surface, credential)] = identity

    def set_expired(self, surface: str, credential: str, expired: bool = True) -> None:
        key = (surface, credential)
        if expired:
            self._expired.add(key)
        else:
            self._expired.discard(key)

    def verify(
        self,
        *,
        surface: str,
        credential: str,
        webhook_envelope: dict[str, Any] | None,
        now: float,
    ) -> VerifiedIdentity:
        del now
        self.calls.append((surface, credential, webhook_envelope))
        key = (surface, credential)
        if key in self._expired:
            raise SurfaceVerificationFailure("credential_expired")
        try:
            return self._credentials[key]
        except KeyError as exc:
            raise SurfaceVerificationFailure("credential_invalid") from exc


@dataclass(frozen=True, slots=True)
class AuditIntent:
    """A safe, test-only audit intent; it is not durable audit evidence."""

    stage: str
    outcome: str
    graft_surface: str
    graft_tenant_id: str | None
    graft_principal_id: str | None
    graft_run_id: str | None
    graft_deny_code: str | None
    durable: bool = False


class AuditIntentRecorder:
    """Records redacted audit intent for tests, never a durable audit chain."""

    def __init__(self) -> None:
        self.records: list[AuditIntent] = []

    def record(
        self,
        *,
        stage: str,
        outcome: str,
        surface: str,
        identity: VerifiedIdentity | None = None,
        run_id: str | None = None,
        deny_code: str | None = None,
    ) -> None:
        self.records.append(
            AuditIntent(
                stage,
                outcome,
                surface,
                None if identity is None else identity.graft_tenant_id,
                None if identity is None else identity.graft_principal_id,
                run_id,
                deny_code,
            )
        )


def _iso_instant(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=UTC).isoformat().replace("+00:00", "Z")


def _epoch_instant(value: str) -> float:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.timestamp()
    except ValueError as exc:
        raise SurfaceVerificationFailure("resolution_expired") from exc


class TestOnlyOpaqueTokenService:
    """A test-only Token Service with opaque tokens and no signing key.

    This is intentionally not Task 5.  Tokens are random opaque handles for
    protocol tests; no signing key, JWKS, or signing isolation exists here.
    """

    label = "test-only opaque token service; not Task 5 JWKS/signing isolation"

    def __init__(
        self,
        verifier: SurfaceVerifier,
        *,
        resolution_ttl_seconds: float = 30.0,
        clock: Callable[[], float] = time.time,
        allowed_peer_identity: str = "harness-api",
        audit: AuditIntentRecorder | None = None,
    ) -> None:
        if resolution_ttl_seconds <= 0:
            raise ValueError("resolution TTL must be positive")
        self.verifier = verifier
        self.resolution_ttl_seconds = resolution_ttl_seconds
        self.clock = clock
        self.allowed_peer_identity = allowed_peer_identity
        self.audit = audit or AuditIntentRecorder()
        self._tokens: dict[str, tuple[str, str, frozenset[str]]] = {}

    def resolve(self, request: ResolutionRequest, *, peer_identity: str) -> ResolutionResponse:
        if peer_identity != self.allowed_peer_identity:
            self.audit.record(
                stage="surface_resolution",
                outcome="deny",
                surface=request.graft_surface,
                deny_code="mtls_peer_not_allowlisted",
            )
            return ResolutionResponse(
                "deny", request.graft_request_correlation_id, deny_code="mtls_peer_not_allowlisted"
            )
        try:
            identity = self.verifier.verify(
                surface=request.graft_surface,
                credential=request.graft_surface_credential,
                webhook_envelope=request.graft_webhook_envelope,
                now=self.clock(),
            )
        except SurfaceVerificationFailure as exc:
            self.audit.record(
                stage="surface_resolution",
                outcome="deny",
                surface=request.graft_surface,
                deny_code=exc.code,
            )
            return ResolutionResponse(
                "deny", request.graft_request_correlation_id, deny_code=exc.code
            )
        fingerprint = (
            None
            if request.graft_webhook_envelope is None
            else canonical_webhook_fingerprint(request.graft_webhook_envelope)
        )
        expiry = _iso_instant(self.clock() + self.resolution_ttl_seconds)
        self.audit.record(
            stage="surface_resolution",
            outcome="allow",
            surface=request.graft_surface,
            identity=identity,
        )
        return ResolutionResponse(
            "allow",
            request.graft_request_correlation_id,
            identity,
            fingerprint,
            expiry,
            self.verifier.revision,
        )

    def mint(self, request: MintRequest, *, peer_identity: str) -> MintResponse:
        if peer_identity != self.allowed_peer_identity:
            self.audit.record(
                stage="capability_mint",
                outcome="deny",
                surface=request.graft_surface,
                run_id=request.graft_run_id,
                deny_code="mtls_peer_not_allowlisted",
            )
            return MintResponse(
                "deny", request.graft_request_correlation_id, deny_code="mtls_peer_not_allowlisted"
            )
        try:
            if _epoch_instant(request.graft_first_resolution.expires_at) <= self.clock():
                raise SurfaceVerificationFailure("resolution_expired")
            if request.graft_first_resolution.verifier_revision != self.verifier.revision:
                raise SurfaceVerificationFailure("verifier_revision_changed")
            identity = self.verifier.verify(
                surface=request.graft_surface,
                credential=request.graft_surface_credential,
                webhook_envelope=request.graft_webhook_envelope,
                now=self.clock(),
            )
        except SurfaceVerificationFailure as exc:
            self.audit.record(
                stage="capability_mint",
                outcome="deny",
                surface=request.graft_surface,
                run_id=request.graft_run_id,
                deny_code=exc.code,
            )
            return MintResponse("deny", request.graft_request_correlation_id, deny_code=exc.code)
        fingerprint = (
            None
            if request.graft_webhook_envelope is None
            else canonical_webhook_fingerprint(request.graft_webhook_envelope)
        )
        token = "graft-test-only." + secrets.token_urlsafe(32)
        # The scope is deliberately read-only for every Phase 1 test identity,
        # and especially for system-initiated Runs.  No signing material exists.
        self._tokens[token] = (request.graft_run_id, identity.graft_tenant_id, frozenset({"read"}))
        self.audit.record(
            stage="capability_mint",
            outcome="allow",
            surface=request.graft_surface,
            identity=identity,
            run_id=request.graft_run_id,
        )
        return MintResponse(
            "allow",
            request.graft_request_correlation_id,
            identity,
            fingerprint,
            request.graft_run_id,
            token,
        )

    def token_scope(self, token: str) -> frozenset[str] | None:
        record = self._tokens.get(token)
        return None if record is None else record[2]
