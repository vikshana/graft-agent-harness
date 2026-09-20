"""Harness-owned two-call Run initiation and immutable replay test double."""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from authority.protocol import (
    FirstResolution,
    MintRequest,
    ResolutionRequest,
    VerifiedIdentity,
    canonical_webhook_fingerprint,
)

from .authority_client import AuthorityClient

ReplayResult = Literal["new", "existing", "conflict"]


@dataclass(frozen=True, slots=True)
class RunBinding:
    graft_tenant_id: str
    graft_harness_replay_key: str
    graft_run_id: str
    graft_event_fingerprint: str | None
    graft_verified_identity: VerifiedIdentity
    graft_service_identity: str
    graft_initiation_mode: str
    graft_resolution_expires_at: str
    graft_verifier_revision: str

    def comparison_tuple(self) -> tuple[Any, ...]:
        return (
            self.graft_event_fingerprint,
            self.graft_verified_identity,
            self.graft_service_identity,
            self.graft_initiation_mode,
        )


@dataclass(frozen=True, slots=True)
class ReplayDisposition:
    graft_replay_result: ReplayResult
    binding: RunBinding


class RunBindingRepository:
    """Thread-safe insert-once repository double.

    This models the atomic operation shape only.  It is intentionally not a
    PostgreSQL repository and therefore is not evidence for durable replay,
    RLS, or durable audit (Tasks 3/4).
    """

    def __init__(self, *, run_id_factory: Any = None) -> None:
        self._records: dict[tuple[str, str], RunBinding] = {}
        self._lock = threading.Lock()
        self._run_id_factory = run_id_factory or (lambda: "graft_run_" + uuid.uuid4().hex)

    @property
    def records(self) -> tuple[RunBinding, ...]:
        with self._lock:
            return tuple(self._records.values())

    def bind(
        self,
        *,
        graft_tenant_id: str,
        graft_harness_replay_key: str,
        event_fingerprint: str | None,
        identity: VerifiedIdentity,
        expires_at: str,
        verifier_revision: str,
    ) -> ReplayDisposition:
        key = (graft_tenant_id, graft_harness_replay_key)
        with self._lock:
            existing = self._records.get(key)
            if existing is None:
                candidate = RunBinding(
                    graft_tenant_id,
                    graft_harness_replay_key,
                    self._run_id_factory(),
                    event_fingerprint,
                    identity,
                    identity.graft_service_identity,
                    identity.graft_initiation_mode,
                    expires_at,
                    verifier_revision,
                )
                self._records[key] = candidate
                return ReplayDisposition("new", candidate)
            candidate_tuple = (
                event_fingerprint,
                identity,
                identity.graft_service_identity,
                identity.graft_initiation_mode,
            )
            if existing.comparison_tuple() == candidate_tuple:
                return ReplayDisposition("existing", existing)
            return ReplayDisposition("conflict", existing)


@dataclass(frozen=True, slots=True)
class RunInitiationOutcome:
    graft_replay_result: ReplayResult | None
    graft_run_id: str | None
    graft_capability_token: str | None
    graft_code: str


def _replay_key(surface: str, envelope: dict[str, Any] | None, supplied: str | None) -> str:
    if supplied is not None:
        if not supplied:
            raise ValueError("replay key cannot be empty")
        # The caller may supply a stable source delivery identity, but the
        # stored key is still namespaced and never contains a raw credential.
        material = {"surface": surface, "source_key": supplied}
    elif envelope is not None:
        material = {
            "surface": surface,
            "source": envelope["graft_source"]["graft_source_ref"],
            "delivery": envelope["graft_delivery"]["graft_delivery_ref"],
        }
    else:
        raise ValueError("a non-webhook initiation requires a stable replay key")
    encoded = json.dumps(
        material, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    return "graft_replay_" + hashlib.sha256(encoded).hexdigest()


class HarnessRunInitiationCoordinator:
    """Implements exactly the accepted first-allow/bind/second-mint flow."""

    def __init__(
        self,
        authority_client: AuthorityClient,
        repository: RunBindingRepository | None = None,
        *,
        clock: Any = time.time,
    ) -> None:
        self.authority_client = authority_client
        self.repository = repository or RunBindingRepository()
        self.clock = clock

    def initiate(
        self,
        *,
        graft_surface: str,
        graft_surface_credential: str,
        graft_webhook_envelope: dict[str, Any] | None = None,
        graft_request_correlation_id: str = "graft-correlation-test",
        graft_harness_replay_key: str | None = None,
    ) -> RunInitiationOutcome:
        request = ResolutionRequest(
            graft_surface,
            graft_surface_credential,
            graft_webhook_envelope,
            graft_request_correlation_id,
        )
        first = self.authority_client.resolve(request)
        if first.decision != "allow" or first.identity is None:
            return RunInitiationOutcome(None, None, None, first.deny_code or "credential_invalid")
        if first.expires_at is None or first.verifier_revision is None:
            return RunInitiationOutcome(None, None, None, "contract_violation")
        fingerprint = first.event_fingerprint
        if graft_webhook_envelope is not None:
            calculated = canonical_webhook_fingerprint(graft_webhook_envelope)
            if fingerprint != calculated:
                return RunInitiationOutcome(None, None, None, "binding_conflict")
        replay_key = _replay_key(graft_surface, graft_webhook_envelope, graft_harness_replay_key)
        disposition = self.repository.bind(
            graft_tenant_id=first.identity.graft_tenant_id,
            graft_harness_replay_key=replay_key,
            event_fingerprint=fingerprint,
            identity=first.identity,
            expires_at=first.expires_at,
            verifier_revision=first.verifier_revision,
        )
        if disposition.graft_replay_result == "conflict":
            return RunInitiationOutcome("conflict", None, None, "binding_conflict")
        binding = disposition.binding
        try:
            expires_at = datetime.fromisoformat(
                binding.graft_resolution_expires_at.replace("Z", "+00:00")
            )
            if expires_at.timestamp() <= self.clock():
                return RunInitiationOutcome(
                    disposition.graft_replay_result,
                    binding.graft_run_id,
                    None,
                    "resolution_expired",
                )
        except ValueError:
            return RunInitiationOutcome(
                disposition.graft_replay_result,
                binding.graft_run_id,
                None,
                "contract_violation",
            )
        mint = self.authority_client.mint(
            MintRequest(
                graft_surface,
                graft_surface_credential,
                graft_webhook_envelope,
                binding.graft_run_id,
                FirstResolution(
                    binding.graft_resolution_expires_at,
                    binding.graft_verifier_revision,
                    binding.graft_event_fingerprint,
                ),
                graft_request_correlation_id,
            )
        )
        if mint.decision != "allow" or mint.identity is None or mint.capability_token is None:
            return RunInitiationOutcome(
                disposition.graft_replay_result,
                binding.graft_run_id,
                None,
                mint.deny_code or "credential_invalid",
            )
        if (
            mint.graft_run_id != binding.graft_run_id
            or mint.identity != binding.graft_verified_identity
            or mint.identity.graft_service_identity != binding.graft_service_identity
            or mint.identity.graft_initiation_mode != binding.graft_initiation_mode
            or mint.event_fingerprint != binding.graft_event_fingerprint
        ):
            return RunInitiationOutcome(
                disposition.graft_replay_result,
                binding.graft_run_id,
                None,
                "binding_conflict",
            )
        return RunInitiationOutcome(
            disposition.graft_replay_result,
            binding.graft_run_id,
            mint.capability_token,
            "ok",
        )
