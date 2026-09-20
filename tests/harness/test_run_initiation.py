from __future__ import annotations

import pytest

from authority.protocol import (
    AuditActor,
    MintRequest,
    MintResponse,
    ResolutionRequest,
    ResolutionResponse,
    VerifiedIdentity,
)
from authority.service import (
    DeterministicSurfaceVerifier,
)
from authority.service import (
    TestOnlyOpaqueTokenService as OpaqueTokenService,
)
from harness.authority_client import InProcessAuthorityClient
from harness.run_initiation import HarnessRunInitiationCoordinator, RunBindingRepository


def identity(principal: str = "principal-1") -> VerifiedIdentity:
    actor = AuditActor(principal, "tenant-1", ("role-reader",), "webhook", "user_initiated", "test")
    return VerifiedIdentity(
        principal, "tenant-1", ("role-reader",), "user_initiated", "authority", actor
    )


def envelope(event_ref: str = "event-1") -> dict[str, object]:
    return {
        "graft_envelope_version": "v1",
        "graft_source": {"graft_source_ref": "source-1", "graft_source_type": "alertmanager"},
        "graft_event": {"graft_event_ref": event_ref, "graft_event_type": "alert"},
        "graft_delivery": {"graft_delivery_ref": "delivery-1", "graft_delivery_sequence": "1"},
        "graft_alert": {
            "graft_alert_name": "CPU high",
            "graft_alert_status": "firing",
            "graft_alert_labels": {"severity": "warning"},
            "graft_alert_annotations": {},
        },
    }


def setup() -> tuple[
    HarnessRunInitiationCoordinator, DeterministicSurfaceVerifier, RunBindingRepository
]:
    credential = "raw \u03bb credential"
    verifier = DeterministicSurfaceVerifier({("webhook", credential): identity()})
    repository = RunBindingRepository(run_id_factory=lambda: "graft_run_fixed")
    coordinator = HarnessRunInitiationCoordinator(
        InProcessAuthorityClient(OpaqueTokenService(verifier)), repository
    )
    return coordinator, verifier, repository


@pytest.mark.unit
def test_replay_is_new_then_existing_and_mint_retry_does_not_create_second_run() -> None:
    coordinator, verifier, repository = setup()
    first = coordinator.initiate(
        graft_surface="webhook",
        graft_surface_credential="raw \u03bb credential",
        graft_webhook_envelope=envelope(),
        graft_harness_replay_key="source-1/delivery-1",
    )
    second = coordinator.initiate(
        graft_surface="webhook",
        graft_surface_credential="raw \u03bb credential",
        graft_webhook_envelope=envelope(),
        graft_harness_replay_key="source-1/delivery-1",
    )
    assert first.graft_replay_result == "new"
    assert second.graft_replay_result == "existing"
    assert first.graft_run_id == second.graft_run_id == "graft_run_fixed"
    assert first.graft_capability_token is not None
    assert second.graft_capability_token is not None
    assert len(repository.records) == 1
    assert len(verifier.calls) == 4


@pytest.mark.unit
def test_same_replay_key_with_changed_valid_identity_is_conflict() -> None:
    coordinator, verifier, repository = setup()
    assert (
        coordinator.initiate(
            graft_surface="webhook",
            graft_surface_credential="raw \u03bb credential",
            graft_webhook_envelope=envelope(),
            graft_harness_replay_key="same-key",
        ).graft_replay_result
        == "new"
    )
    verifier.set_identity("webhook", "raw \u03bb credential", identity("principal-2"))
    changed = coordinator.initiate(
        graft_surface="webhook",
        graft_surface_credential="raw \u03bb credential",
        graft_webhook_envelope=envelope(),
        graft_harness_replay_key="same-key",
    )
    assert changed.graft_replay_result == "conflict"
    assert changed.graft_code == "binding_conflict"
    assert changed.graft_capability_token is None
    assert len(repository.records) == 1


@pytest.mark.unit
def test_fresh_second_result_mismatch_is_discarded_without_new_run() -> None:
    coordinator, verifier, repository = setup()
    original = coordinator.authority_client
    first = coordinator.initiate(
        graft_surface="webhook",
        graft_surface_credential="raw \u03bb credential",
        graft_webhook_envelope=envelope(),
        graft_harness_replay_key="fresh-result",
    )
    assert first.graft_code == "ok"

    class ChangingClient:
        def resolve(self, request: ResolutionRequest) -> ResolutionResponse:
            return original.resolve(request)

        def mint(self, request: MintRequest) -> MintResponse:
            verifier.set_identity("webhook", "raw \u03bb credential", identity("principal-3"))
            return original.mint(request)

    coordinator.authority_client = ChangingClient()
    changed = coordinator.initiate(
        graft_surface="webhook",
        graft_surface_credential="raw \u03bb credential",
        graft_webhook_envelope=envelope(),
        graft_harness_replay_key="another-key",
    )
    assert changed.graft_code == "binding_conflict"
    assert changed.graft_capability_token is None
    assert len(repository.records) == 2


@pytest.mark.unit
def test_first_resolution_expiry_prevents_second_mint() -> None:
    now = [1000.0]
    credential = "credential"
    verifier = DeterministicSurfaceVerifier({("api", credential): identity()})
    service = OpaqueTokenService(verifier, resolution_ttl_seconds=2, clock=lambda: now[0])
    repository = RunBindingRepository(run_id_factory=lambda: "graft_run_expiry")
    coordinator = HarnessRunInitiationCoordinator(
        InProcessAuthorityClient(service), repository, clock=lambda: now[0]
    )
    # First call and mint are immediate and succeed.
    first = coordinator.initiate(
        graft_surface="api",
        graft_surface_credential=credential,
        graft_harness_replay_key="expiry-key",
    )
    assert first.graft_code == "ok"
    now[0] = 1003.0
    expired = coordinator.initiate(
        graft_surface="api",
        graft_surface_credential=credential,
        graft_harness_replay_key="expiry-key",
    )
    assert expired.graft_code == "resolution_expired"
    assert len(repository.records) == 1
    assert len(verifier.calls) == 3
