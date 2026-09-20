from __future__ import annotations

from collections.abc import Mapping

import pytest

from harness.contracts import ERROR_CODES, AlertTrigger, ErrorEnvelope, RunCreateRequest
from harness.http_api import HarnessHttpApplication, VerifiedIdentity
from harness.service import HarnessService
from harness.store import IdempotencyConflict, TenantBoundaryError


def request(key: str = "provider-1", summary: str = "CPU is high") -> RunCreateRequest:
    return RunCreateRequest(
        graft_tenant_id="tenant-provider",
        graft_principal_id="principal-provider",
        idempotency_key=key,
        trigger=AlertTrigger("alertmanager", "alert-provider", summary, "fp-provider"),
    )


@pytest.mark.contract
def test_provider_supports_create_retrieve_cancel_and_exclusive_replay() -> None:
    service = HarnessService()
    run = service.create_run(request())
    assert run.graft_run_id
    assert service.get_run("tenant-provider", run.graft_run_id).graft_run_id == run.graft_run_id
    events = service.replay_events("tenant-provider", run.graft_run_id)
    assert events and events[-1].event_type == "done"
    replayed = service.replay_events("tenant-provider", run.graft_run_id, events[0].graft_event_id)
    assert [event.graft_event_id for event in replayed] == [
        event.graft_event_id for event in events[1:]
    ]
    assert service.cancel_run("tenant-provider", run.graft_run_id).outcome == "already_terminal"


@pytest.mark.contract
def test_provider_idempotency_and_tenant_boundary_semantics() -> None:
    service = HarnessService()
    first = service.create_run(request())
    assert service.create_run(request()).graft_run_id == first.graft_run_id
    with pytest.raises(IdempotencyConflict):
        service.create_run(request(summary="different"))
    with pytest.raises(TenantBoundaryError):
        service.get_run("tenant-other", first.graft_run_id)


@pytest.mark.contract
def test_reference_provider_boundary_is_not_identity_authority_evidence() -> None:
    # This is deliberately a visible contract test: the synchronous WSGI/
    # in-memory provider supports the semantic operation set, but production
    # credential verification remains an implementation-pending seam.
    service = HarnessService()
    assert service.create_run(request()).graft_principal_id == "principal-provider"


@pytest.mark.contract
def test_provider_can_verify_every_standard_error_variant() -> None:
    for code in ERROR_CODES:
        error = ErrorEnvelope(code, "contract example", "request-provider")
        assert error.to_contract_dict()["graft_code"] == code


@pytest.mark.contract
def test_reference_http_provider_uses_out_of_band_identity_and_canonical_wire_fields() -> None:
    import io
    import json

    body = json.dumps(
        {
            "graft_trigger": {
                "graft_source": "alertmanager",
                "graft_alert_id": "alert-canonical",
                "graft_summary": "CPU is high",
                "graft_fingerprint": "fp-canonical",
            }
        }
    ).encode()
    statuses: list[str] = []
    application = HarnessHttpApplication(
        test_verified_identity=VerifiedIdentity("tenant-verified", "principal-verified")
    )
    response = application(
        {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/v1/runs",
            "CONTENT_LENGTH": str(len(body)),
            "HTTP_X_GRAFT_IDEMPOTENCY_KEY": "canonical-1",
            "wsgi.input": io.BytesIO(body),
        },
        lambda status, _: statuses.append(status),
    )
    assert statuses[0].startswith("201")
    run = json.loads(response[0])
    assert run["graft_tenant_id"] == "tenant-verified"
    assert run["graft_principal_id"] == "principal-verified"
    assert "graft_finding_ref" in run
    assert "finding" not in run


@pytest.mark.contract
def test_reference_http_provider_rejects_caller_identity_fields() -> None:
    import io
    import json

    body = json.dumps(
        {
            "graft_tenant_id": "forged",
            "graft_trigger": {
                "graft_source": "alertmanager",
                "graft_alert_id": "alert-canonical",
                "graft_summary": "CPU is high",
                "graft_fingerprint": "fp-canonical",
            },
        }
    ).encode()
    statuses: list[str] = []
    response = HarnessHttpApplication()(
        {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/v1/runs",
            "CONTENT_LENGTH": str(len(body)),
            "HTTP_X_GRAFT_IDEMPOTENCY_KEY": "canonical-2",
            "wsgi.input": io.BytesIO(body),
        },
        lambda status, _: statuses.append(status),
    )
    assert statuses[0].startswith("400")
    assert json.loads(response[0])["graft_code"] == "invalid_request"


@pytest.mark.contract
def test_reference_http_provider_requires_canonical_idempotency_and_validates_cancel() -> None:
    import io
    import json

    body = json.dumps(
        {
            "graft_trigger": {
                "graft_source": "alertmanager",
                "graft_alert_id": "alert-missing-key",
                "graft_summary": "CPU is high",
                "graft_fingerprint": "fp-missing-key",
            }
        }
    ).encode()
    statuses: list[str] = []
    response = HarnessHttpApplication()(
        {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/v1/runs",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        },
        lambda status, _: statuses.append(status),
    )
    assert statuses[0].startswith("400")
    assert json.loads(response[0])["graft_code"] == "invalid_request"

    cancel_body = json.dumps({"graft_tenant_id": "forged"}).encode()
    statuses.clear()
    response = HarnessHttpApplication()(
        {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/v1/runs/not-visible/cancel",
            "CONTENT_LENGTH": str(len(cancel_body)),
            "wsgi.input": io.BytesIO(cancel_body),
        },
        lambda status, _: statuses.append(status),
    )
    assert statuses[0].startswith("400")
    assert json.loads(response[0])["graft_code"] == "invalid_request"


@pytest.mark.contract
def test_reference_http_provider_maps_version_and_replay_mode_errors() -> None:
    import io
    import json

    body = json.dumps(
        {
            "graft_contract_version": "v2",
            "graft_trigger": {
                "graft_source": "alertmanager",
                "graft_alert_id": "alert-version",
                "graft_summary": "CPU is high",
                "graft_fingerprint": "fp-version",
            },
        }
    ).encode()
    statuses: list[str] = []
    response = HarnessHttpApplication()(
        {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/v1/runs",
            "CONTENT_LENGTH": str(len(body)),
            "HTTP_X_GRAFT_IDEMPOTENCY_KEY": "version-1",
            "wsgi.input": io.BytesIO(body),
        },
        lambda status, _: statuses.append(status),
    )
    assert statuses[0].startswith("400")
    assert json.loads(response[0])["graft_code"] == "unsupported_contract_version"

    statuses.clear()
    response = HarnessHttpApplication()(
        {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/v1/runs/not-visible/events",
            "RAW_URI": "/v1/runs/not-visible/events?graft_replay_mode=bogus",
            "wsgi.input": io.BytesIO(b""),
        },
        lambda status, _: statuses.append(status),
    )
    assert statuses[0].startswith("400")
    assert json.loads(response[0])["graft_code"] == "invalid_request"

    statuses.clear()
    response = HarnessHttpApplication()(
        {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/v1/runs/not-visible/events",
            "RAW_URI": "/v1/runs/not-visible/events?graft_replay_mode=follow",
            "wsgi.input": io.BytesIO(b""),
        },
        lambda status, _: statuses.append(status),
    )
    assert statuses[0].startswith("400")
    assert json.loads(response[0])["graft_code"] == "invalid_request"


@pytest.mark.contract
def test_provider_replay_page_and_cancel_outcome_variants_are_canonical() -> None:
    service = HarnessService()
    run = service.create_run(request("page-1"))
    page = service.replay_page("tenant-provider", run.graft_run_id, limit=2)
    assert page.to_contract_dict()["graft_next_after_event_id"] == page.events[-1].graft_event_id
    assert page.to_contract_dict()["graft_has_more"] is True

    class PendingService(HarnessService):
        def _execute(self, request: RunCreateRequest, graft_run_id: str) -> None:
            del request, graft_run_id

    pending = PendingService()
    pending_run = pending.create_run(request("cancel-1"))
    first = pending.cancel_run("tenant-provider", pending_run.graft_run_id)
    second = pending.cancel_run("tenant-provider", pending_run.graft_run_id)
    assert first.outcome == "accepted"
    assert second.outcome == "already_requested"


@pytest.mark.contract
def test_provider_exercises_every_declared_supported_http_error_and_outcome() -> None:
    import io
    import json

    def call(
        application: HarnessHttpApplication,
        method: str,
        path: str,
        value: Mapping[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[str, dict[str, object]]:
        raw = json.dumps(value or {}).encode()
        environ: dict[str, object] = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path.split("?", 1)[0],
            "RAW_URI": path,
            "CONTENT_LENGTH": str(len(raw)),
            "wsgi.input": io.BytesIO(raw),
        }
        for name, header_value in (headers or {}).items():
            environ[f"HTTP_{name.upper().replace('-', '_')}"] = header_value
        statuses: list[str] = []
        result = application(environ, lambda status, _: statuses.append(status))
        return statuses[0], json.loads(result[0])

    application = HarnessHttpApplication()
    create_body = {
        "graft_trigger": {
            "graft_source": "alertmanager",
            "graft_alert_id": "declared-errors",
            "graft_summary": "CPU is high",
            "graft_fingerprint": "declared-errors-fingerprint",
        }
    }
    status, value = call(application, "POST", "/v1/runs", create_body)
    assert status.startswith("400") and value["graft_code"] == "invalid_request"
    status, value = call(
        application,
        "POST",
        "/v1/runs",
        {**create_body, "graft_contract_version": "v2"},
        {"X-Graft-Idempotency-Key": "declared-errors-1"},
    )
    assert status.startswith("400") and value["graft_code"] == "unsupported_contract_version"
    status, value = call(
        application,
        "POST",
        "/v1/runs",
        create_body,
        {"X-Graft-Idempotency-Key": "declared-errors-1"},
    )
    assert status.startswith("201") and "graft_run_id" in value
    run_id = str(value["graft_run_id"])
    status, value = call(
        application,
        "POST",
        "/v1/runs",
        {
            **create_body,
            "graft_trigger": {**create_body["graft_trigger"], "graft_summary": "changed"},
        },
        {"X-Graft-Idempotency-Key": "declared-errors-1"},
    )
    assert status.startswith("409") and value["graft_code"] == "idempotency_conflict"
    status, value = call(application, "GET", "/v1/runs/missing-run")
    assert status.startswith("404") and value["graft_code"] == "not_found"
    status, value = call(
        application,
        "POST",
        "/v1/runs/missing-run/cancel",
        {"graft_contract_version": "v2"},
    )
    assert status.startswith("400") and value["graft_code"] == "unsupported_contract_version"
    status, value = call(application, "POST", "/v1/runs/missing-run/cancel")
    assert status.startswith("404") and value["graft_code"] == "not_found"
    status, value = call(
        application,
        "GET",
        "/v1/runs/missing-run/events?after_graft_event_id=not-an-integer",
    )
    assert status.startswith("400") and value["graft_code"] == "cursor_invalid"
    status, value = call(
        application,
        "GET",
        "/v1/runs/missing-run/events?graft_replay_mode=replay",
    )
    assert status.startswith("404") and value["graft_code"] == "not_found"

    service = application.service
    pending = HarnessService()
    pending_run = pending.create_run(request("declared-outcomes"))
    assert (
        pending.cancel_run("tenant-provider", pending_run.graft_run_id).outcome
        == "already_terminal"
    )
    del service, run_id
