from __future__ import annotations

import json
from typing import Literal

import pytest

from authority.protocol import (
    AuditActor,
    AuthorityProtocolError,
    ResolutionRequest,
    VerifiedIdentity,
)
from authority.service import (
    AuditIntentRecorder,
    DeterministicSurfaceVerifier,
)
from authority.service import (
    TestOnlyOpaqueTokenService as OpaqueTokenService,
)


def identity(
    *,
    principal: str | None = "principal-1",
    mode: Literal["user_initiated", "system_initiated"] = "user_initiated",
) -> VerifiedIdentity:
    actor = AuditActor(principal, "tenant-1", ("role-reader",), "webhook", mode, "test-verified")
    return VerifiedIdentity(principal, "tenant-1", ("role-reader",), mode, "authority-test", actor)


def webhook() -> dict[str, object]:
    return {
        "graft_envelope_version": "v1",
        "graft_source": {"graft_source_ref": "source-1", "graft_source_type": "alertmanager"},
        "graft_event": {"graft_event_ref": "event-1", "graft_event_type": "alert"},
        "graft_delivery": {"graft_delivery_ref": "delivery-1", "graft_delivery_sequence": "1"},
        "graft_alert": {
            "graft_alert_name": "CPU high",
            "graft_alert_status": "firing",
            "graft_alert_labels": {},
            "graft_alert_annotations": {},
        },
    }


def test_service_returns_only_allow_or_deny_and_never_leaks_credential() -> None:
    credential = "  raw\u03bb\u0301 credential  "
    audit = AuditIntentRecorder()
    verifier = DeterministicSurfaceVerifier({("webhook", credential): identity()})
    service = OpaqueTokenService(verifier, audit=audit)
    request = ResolutionRequest("webhook", credential, webhook(), "correlation")
    allowed = service.resolve(request, peer_identity="harness-api")
    assert allowed.decision == "allow"
    assert credential not in json.dumps(allowed.to_dict())
    denied = service.resolve(
        ResolutionRequest("webhook", credential + "x", webhook(), "denied"),
        peer_identity="harness-api",
    )
    assert denied.decision == "deny"
    assert credential not in json.dumps(denied.to_dict())
    assert credential not in json.dumps(audit.records, default=str)

    # A webhook request without its envelope is rejected before verification.
    with pytest.raises(AuthorityProtocolError):
        ResolutionRequest.from_dict(
            {
                "graft_authority_schema_version": "v1",
                "graft_surface": "webhook",
                "graft_surface_credential": credential,
                "graft_request_correlation_id": "malformed",
            }
        )


def test_exact_credential_including_unicode_is_verified_twice() -> None:
    credential = "  raw\u03bb\u0301 credential  "
    verifier = DeterministicSurfaceVerifier({("api", credential): identity()})
    service = OpaqueTokenService(verifier)
    first = service.resolve(
        ResolutionRequest("api", credential, None, "one"), peer_identity="harness-api"
    )
    assert first.decision == "allow"
    assert len(verifier.calls) == 1
    assert verifier.calls[0][1] == credential
    assert credential not in json.dumps(first.to_dict())


def test_system_initiated_scope_is_read_only_and_token_is_test_only() -> None:
    system_identity = identity(principal=None, mode="system_initiated")
    credential = "schedule-secret"
    verifier = DeterministicSurfaceVerifier({("schedule", credential): system_identity})
    service = OpaqueTokenService(verifier)
    first = service.resolve(
        ResolutionRequest("schedule", credential, None, "one"), peer_identity="harness-api"
    )
    assert first.decision == "allow"
    assert first.identity is not None
    from authority.protocol import FirstResolution, MintRequest

    mint = service.mint(
        MintRequest(
            "schedule",
            credential,
            None,
            "graft_run_system",
            FirstResolution(first.expires_at or "", first.verifier_revision or "", None),
            "two",
        ),
        peer_identity="harness-api",
    )
    assert mint.decision == "allow"
    assert mint.capability_token is not None
    assert mint.capability_token.startswith("graft-test-only.")
    assert service.token_scope(mint.capability_token) == frozenset({"read"})
    assert "signing" in service.label


@pytest.mark.unit
def test_non_allowlisted_tls_peer_is_typed_deny_without_identity_or_token() -> None:
    credential = "credential"
    audit = AuditIntentRecorder()
    service = OpaqueTokenService(
        DeterministicSurfaceVerifier({("api", credential): identity()}), audit=audit
    )
    response = service.resolve(
        ResolutionRequest("api", credential, None, "one"), peer_identity="other"
    )
    assert response.to_dict() == {
        "graft_authority_schema_version": "v1",
        "graft_decision": "deny",
        "graft_deny_code": "mtls_peer_not_allowlisted",
        "graft_request_correlation_id": "one",
    }
    assert audit.records[0].graft_tenant_id is None
