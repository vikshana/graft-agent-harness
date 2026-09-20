from __future__ import annotations

import json

import pytest

from authority.protocol import (
    AuthorityProtocolError,
    MintRequest,
    ResolutionRequest,
    canonical_webhook_bytes,
    canonical_webhook_fingerprint,
)


def webhook() -> dict[str, object]:
    return {
        "graft_envelope_version": "v1",
        "graft_source": {"graft_source_type": "alertmanager", "graft_source_ref": "source-1"},
        "graft_event": {"graft_event_type": "alert", "graft_event_ref": "event-1"},
        "graft_delivery": {"graft_delivery_sequence": "1", "graft_delivery_ref": "delivery-1"},
        "graft_alert": {
            "graft_alert_status": "firing",
            "graft_alert_name": "CPU high",
            "graft_alert_labels": {"β": "значение", "severity": "warning"},
            "graft_alert_annotations": {"summary": "high"},
        },
    }


@pytest.mark.contract
def test_webhook_fingerprint_is_order_independent_but_semantic_changes_differ() -> None:
    first = webhook()
    second = json.loads(json.dumps(first, ensure_ascii=False))
    second["graft_source"] = {"graft_source_ref": "source-1", "graft_source_type": "alertmanager"}
    second["graft_alert"] = {
        "graft_alert_annotations": {"summary": "high"},
        "graft_alert_labels": {"severity": "warning", "β": "значение"},
        "graft_alert_name": "CPU high",
        "graft_alert_status": "firing",
    }
    assert canonical_webhook_bytes(first) == canonical_webhook_bytes(second)
    assert canonical_webhook_fingerprint(first) == canonical_webhook_fingerprint(second)
    changed = json.loads(json.dumps(first, ensure_ascii=False))
    changed_alert = changed["graft_alert"]
    assert isinstance(changed_alert, dict)
    changed_alert["graft_alert_status"] = "resolved"
    assert canonical_webhook_fingerprint(first) != canonical_webhook_fingerprint(changed)


@pytest.mark.contract
def test_closed_requests_reject_caller_identity_and_surface_mismatch() -> None:
    value = ResolutionRequest(
        "webhook",
        "raw secret  \u03bb",
        webhook(),
        "correlation-1",
    ).to_dict()
    value["graft_tenant_id"] = "forged-tenant"
    with pytest.raises(AuthorityProtocolError):
        ResolutionRequest.from_dict(value)
    value = ResolutionRequest("api", "credential", None, "correlation-2").to_dict()
    value["graft_webhook_envelope"] = webhook()
    with pytest.raises(AuthorityProtocolError):
        ResolutionRequest.from_dict(value)


@pytest.mark.contract
def test_mint_request_requires_first_resolution_and_run_id() -> None:
    value = {
        "graft_authority_schema_version": "v1",
        "graft_surface": "webhook",
        "graft_surface_credential": "credential",
        "graft_webhook_envelope": webhook(),
        "graft_run_id": "graft_run_1",
        "graft_first_resolution": {
            "graft_resolution_expires_at": "2026-09-20T12:00:00Z",
            "graft_verifier_revision": "test-v1",
            "graft_event_fingerprint": canonical_webhook_fingerprint(webhook()),
        },
        "graft_request_correlation_id": "correlation-3",
    }
    assert MintRequest.from_dict(value).graft_run_id == "graft_run_1"
    value["graft_principal_id"] = "forged"
    with pytest.raises(AuthorityProtocolError):
        MintRequest.from_dict(value)
