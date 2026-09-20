from __future__ import annotations

import importlib
import json
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any

import pytest

from harness.contracts import (
    CONTRACT_VERSION,
    EVENT_TYPES,
    AlertTrigger,
    CancelOutcome,
    ContractValidationError,
    ErrorEnvelope,
    EvidencePayload,
    ExternalReference,
    PointerMetadata,
    PointerPayload,
    Run,
    RunCreateRequest,
    RunEvent,
    ToolCallResultPayload,
)

ROOT = Path(__file__).parents[2]
Draft202012Validator = importlib.import_module("jsonschema").Draft202012Validator


def load_json(relative_path: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


@pytest.mark.contract
def test_contract_check_script_validates_all_authorities_and_examples() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_contracts.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.contract
def test_rest_contract_lists_all_operations_and_error_examples() -> None:
    document = load_json("contracts/harness-v1.openapi.json")
    operation_ids = {
        operation["operationId"]
        for path in document["paths"].values()
        for method, operation in path.items()
        if method in {"get", "post"}
    }
    assert operation_ids == {"createRun", "getRun", "replayRunEvents", "cancelRun"}
    examples = document["components"]["examples"]
    assert {
        example["value"].get("graft_code")
        for name, example in examples.items()
        if name
        not in {"Run", "CreateRunRequest", "EventReplayPage", "CancelRequest", "CancelOutcome"}
    } >= {
        "authentication_required",
        "authorisation_denied",
        "invalid_request",
        "not_found",
        "idempotency_conflict",
        "state_conflict",
        "cursor_invalid",
        "replay_cursor_expired",
        "throttled",
        "service_unavailable",
        "internal_error",
    }


@pytest.mark.contract
def test_event_examples_cover_every_fixed_event_variant_and_pointer_rules() -> None:
    document = load_json("contracts/run-events-v1.schema.json")
    examples = {example["graft_event_type"]: example for example in document["examples"]}
    assert set(examples) == EVENT_TYPES
    for event_type, example in examples.items():
        event = RunEvent(
            graft_event_id=example["graft_event_id"],
            graft_run_id=example["graft_run_id"],
            graft_tenant_id=example["graft_tenant_id"],
            event_type=event_type,
            payload=example["graft_payload"],
            created_at=example["graft_created_at"],
        )
        assert event.to_dict()["graft_event_id"] == example["graft_event_id"]

    with pytest.raises(ContractValidationError):
        RunEvent(99, "run-01", "tenant-01", "tool_call_result", {}, "2026-09-20T10:00:00Z")


@pytest.mark.contract
def test_unknown_additive_event_and_fields_are_tolerated() -> None:
    event = RunEvent(
        1,
        "run-01",
        "tenant-01",
        "future_diagnostic_snapshot",
        {"graft_new_field": "safe to ignore", "future_payload": {"x": 1}},
        "2026-09-20T10:00:00Z",
    )
    assert event.event_type not in EVENT_TYPES
    assert event.payload["graft_new_field"] == "safe to ignore"
    assert event.to_contract_dict()["graft_payload"]["graft_new_field"] == "safe to ignore"

    error = ErrorEnvelope("not_found", "not visible", "request-01", {"future_detail": True})
    assert error.to_dict().get("future_detail", True)


@pytest.mark.contract
def test_external_results_are_pointer_only() -> None:
    reference = ExternalReference("tool-result", "graft://artifacts/result-01", graft_byte_length=4)
    assert reference.to_dict()["graft_uri"].startswith("graft://")
    with pytest.raises(ContractValidationError):
        ExternalReference("tool-result", "data:text/plain,secret").validate()
    with pytest.raises(ContractValidationError):
        RunEvent(
            100,
            "run-01",
            "tenant-01",
            "tool_call_result",
            {
                "graft_tool_call_id": "tool-call-01",
                "graft_artifact_ref": {
                    "graft_ref_kind": "tool-result",
                    "graft_uri": "graft://result",
                },
                "graft_raw_result": {"secret": "must not be inline"},
            },
            "2026-09-20T10:00:00Z",
        )

    safe_metadata = PointerMetadata(graft_label="summary", graft_origin="reducer")
    assert (
        ToolCallResultPayload("tool-call-01", reference, safe_metadata).graft_pointer_metadata
        == safe_metadata
    )
    assert PointerPayload(reference, safe_metadata).graft_ref == reference
    assert EvidencePayload("evidence-01", reference, safe_metadata).graft_external_ref == reference

    with pytest.raises(ContractValidationError):
        PointerMetadata(graft_label="x" * 257)


@pytest.mark.contract
def test_contract_version_and_additive_rules_are_explicit() -> None:
    openapi = load_json("contracts/harness-v1.openapi.json")
    events = load_json("contracts/run-events-v1.schema.json")
    manifest = load_json("contracts/harness-mcp-v1.manifest.json")
    assert CONTRACT_VERSION == "v1"
    assert "additions" in openapi["x-graft-versioning"]["rule"]
    assert "new contract major version" in openapi["x-graft-versioning"]["breaking-change"]
    assert "unknown_event_policy" in manifest["compatibility"]
    assert events["x-graft-versioning"]["cursor"].startswith("graft_event_id")


@pytest.mark.contract
def test_mcp_capabilities_have_semantic_rest_operation_parity() -> None:
    openapi = load_json("contracts/harness-v1.openapi.json")
    manifest = load_json("contracts/harness-mcp-v1.manifest.json")
    rest_operation_ids = {
        operation["operationId"]
        for path in openapi["paths"].values()
        for method, operation in path.items()
        if method in {"get", "post"}
    }
    mcp_operations = {tool["x-graft-authority-operation"] for tool in manifest["tools"]}
    assert mcp_operations == {
        "create_run",
        "get_run",
        "cancel_run",
        "replay_run_events",
    }
    assert rest_operation_ids == {"createRun", "getRun", "cancelRun", "replayRunEvents"}
    create = next(tool for tool in manifest["tools"] if tool["name"] == "graft_create_run")
    assert "graft_idempotency_key" in create["inputSchema"]["required"]
    assert create["inputSchema"]["not"]["anyOf"]
    assert {
        "graft_tenant_id",
        "graft_principal_id",
        "graft_identity",
    } <= {field for rule in create["inputSchema"]["not"]["anyOf"] for field in rule["required"]}


@pytest.mark.contract
def test_rest_declares_and_mcp_maps_the_complete_standard_error_model() -> None:
    openapi = load_json("contracts/harness-v1.openapi.json")
    manifest = load_json("contracts/harness-mcp-v1.manifest.json")
    error_codes = set(
        openapi["components"]["schemas"]["ErrorEnvelope"]["properties"]["graft_code"]["enum"]
    )
    declared = set()
    for item in openapi["paths"].values():
        for operation in item.values():
            if isinstance(operation, dict) and "operationId" in operation:
                declared.update(operation["x-graft-declared-error-codes"])
    assert declared == error_codes
    for tool in manifest["tools"]:
        assert set(tool["x-graft-provider-supported-errors"]).issubset(
            set(tool["x-graft-error-codes"])
        )


@pytest.mark.contract
def test_event_and_mcp_schema_examples_validate() -> None:
    event_schema = load_json("contracts/run-events-v1.schema.json")
    Draft202012Validator.check_schema(event_schema)
    validator = Draft202012Validator(event_schema)
    for example in event_schema["examples"]:
        validator.validate(example)

    mcp_schema = load_json("contracts/harness-mcp-v1.schema.json")
    Draft202012Validator.check_schema(mcp_schema)
    manifest = load_json("contracts/harness-mcp-v1.manifest.json")
    manifest.pop("$schema", None)
    manifest.pop("$id", None)
    Draft202012Validator(mcp_schema).validate(manifest)


@pytest.mark.contract
def test_event_schema_enums_match_python_contract_constants() -> None:
    events = load_json("contracts/run-events-v1.schema.json")
    from harness.contracts import ERROR_CODES, RUN_STATUSES, TERMINAL_OUTCOMES

    assert set(events["$defs"]["StatusPayload"]["properties"]["graft_status"]["enum"]) == set(
        RUN_STATUSES
    )
    assert set(events["$defs"]["DonePayload"]["properties"]["graft_outcome"]["enum"]) == set(
        TERMINAL_OUTCOMES
    )
    assert set(events["$defs"]["ErrorPayload"]["properties"]["graft_code"]["enum"]) == set(
        ERROR_CODES
    )


@pytest.mark.contract
def test_pointer_only_schema_rejects_unknown_tool_result_payload_fields() -> None:
    events = load_json("contracts/run-events-v1.schema.json")
    payloads = (
        (
            "ToolCallResultPayload",
            {
                "graft_tool_call_id": "tool-call-01",
                "graft_artifact_ref": {
                    "graft_ref_kind": "tool-result",
                    "graft_uri": "graft://artifacts/result-01",
                },
            },
        ),
        (
            "PointerPayload",
            {
                "graft_ref": {
                    "graft_ref_kind": "plan",
                    "graft_uri": "graft://artifacts/plan-01",
                },
            },
        ),
        (
            "EvidencePayload",
            {
                "graft_evidence_id": "evidence-01",
                "graft_external_ref": {
                    "graft_ref_kind": "log",
                    "graft_uri": "graft://artifacts/log-01",
                },
            },
        ),
    )
    for payload_name, payload in payloads:
        for forbidden_field in (
            "graft_raw",
            "graft_large",
            "graft_blob",
            "graft_content",
            "graft_result",
        ):
            candidate = {
                **payload,
                forbidden_field: "must be rejected",
            }
            with pytest.raises(Exception):  # noqa: B017 - jsonschema is optional and untyped
                Draft202012Validator(events["$defs"][payload_name]).validate(candidate)


@pytest.mark.contract
def test_pointer_event_models_reject_inline_payload_fields() -> None:
    reference = {"graft_ref_kind": "plan", "graft_uri": "graft://artifacts/plan-01"}
    for event_type, payload in (
        ("plan_updated", {"graft_ref": reference, "graft_blob": "inline"}),
        (
            "evidence_added",
            {"graft_evidence_id": "evidence-01", "graft_content": "inline"},
        ),
    ):
        with pytest.raises(ContractValidationError):
            RunEvent(101, "run-01", "tenant-01", event_type, payload, "2026-09-20T10:00:00Z")


@pytest.mark.contract
def test_unknown_event_types_and_fields_remain_additive() -> None:
    events = load_json("contracts/run-events-v1.schema.json")
    validator = Draft202012Validator(events)
    validator.validate(
        {
            "graft_event_id": 99,
            "graft_run_id": "run-01",
            "graft_tenant_id": "tenant-01",
            "graft_event_type": "future_diagnostic_snapshot",
            "graft_event_version": 1,
            "graft_payload": {"graft_future_field": {"graft_hint": "ignore"}},
            "graft_created_at": "2026-09-20T10:00:06Z",
            "graft_contract_version": "v1",
            "graft_future_envelope_field": True,
        }
    )


@pytest.mark.contract
def test_reference_models_validate_against_canonical_schemas() -> None:
    """Catch model field/type drift even when checked-in examples stay unchanged."""

    openapi = load_json("contracts/harness-v1.openapi.json")
    events = load_json("contracts/run-events-v1.schema.json")
    service_run = Run(
        "run-model",
        "tenant-model",
        "principal-model",
        "completed",
        "finding",
        "Investigation result",
        ("read",),
        "2026-09-20T10:00:00Z",
        "2026-09-20T10:00:01Z",
    )
    request = RunCreateRequest(
        "tenant-model",
        AlertTrigger("alertmanager", "alert-model", "CPU is high", "fp-model"),
        "model-key",
        "principal-model",
    )
    values = {
        "RunCreateRequest": request.to_contract_dict(),
        "Run": service_run.to_contract_dict(),
        "CancelOutcome": CancelOutcome(
            "run-model", "already_terminal", "completed"
        ).to_contract_dict(),
        "ErrorEnvelope": ErrorEnvelope(
            "not_found", "not visible", "request-model"
        ).to_contract_dict(),
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        resolver = importlib.import_module("jsonschema").RefResolver.from_schema(openapi)
        for schema_name, value in values.items():
            importlib.import_module("jsonschema").Draft202012Validator(
                {"$ref": f"#/components/schemas/{schema_name}"}, resolver=resolver
            ).validate(value)
    event = RunEvent(
        1,
        "run-model",
        "tenant-model",
        "status",
        {"graft_status": "completed"},
        "2026-09-20T10:00:01Z",
    )
    Draft202012Validator(events).validate(event.to_contract_dict())
