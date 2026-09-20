#!/usr/bin/env python3
"""Check the checked-in v1 contract artefacts without generating code.

This intentionally uses only the Python standard library.  The repository's
contract check is therefore runnable before the development environment is
installed and does not accidentally become coupled to a framework validator.
It checks the invariant portions of JSON Schema/OpenAPI, validates every
checked-in example used by the compatibility suite, and exercises the
additive-versus-breaking fixture policy.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
EVENT_TYPES = {
    "status",
    "token",
    "agent_thought",
    "plan_updated",
    "tool_call_start",
    "tool_call_result",
    "evidence_added",
    "hypothesis_updated",
    "confidence_changed",
    "action_proposed",
    "action_confirmed",
    "action_executed",
    "sub_agent_spawned",
    "hitl_required",
    "budget_consumed",
    "budget_warning",
    "error",
    "done",
}
ERROR_CODES = {
    "authentication_required",
    "authentication_failed",
    "authorisation_denied",
    "invalid_request",
    "unsupported_contract_version",
    "not_found",
    "idempotency_conflict",
    "state_conflict",
    "cursor_invalid",
    "replay_cursor_expired",
    "throttled",
    "request_timeout",
    "service_unavailable",
    "internal_error",
}
RUN_STATUSES = {
    "queued",
    "running",
    "completed",
    "cancelled",
    "failed",
    "cancellation_requested",
}
TERMINAL_OUTCOMES = {"finding", "no_finding", "cancelled", "failed", "timed_out"}
OPERATIONS = {
    "createRun",
    "getRun",
    "replayRunEvents",
    "cancelRun",
}
BASELINE = ROOT / "tests/fixtures/contract-baseline.json"


def load(name: str) -> dict[str, Any]:
    path = CONTRACTS / name
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{name} must contain a JSON object")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_error(example: dict[str, Any], expected_code: str) -> None:
    require(
        example.get("graft_code") == expected_code,
        f"error example mismatch: {expected_code}",
    )
    require(
        isinstance(example.get("graft_message"), str),
        f"missing error message: {expected_code}",
    )
    require(
        isinstance(example.get("graft_request_id"), str),
        f"missing request id: {expected_code}",
    )
    require(
        example.get("graft_contract_version") == "v1",
        f"wrong error version: {expected_code}",
    )
    require(
        isinstance(example.get("graft_details"), dict),
        f"error details must be an object: {expected_code}",
    )


def validate_event(example: dict[str, Any]) -> None:
    required = {
        "graft_event_id",
        "graft_run_id",
        "graft_tenant_id",
        "graft_event_type",
        "graft_event_version",
        "graft_payload",
        "graft_created_at",
        "graft_contract_version",
    }
    require(
        required <= example.keys(), f"event example missing fields: {required - example.keys()}"
    )
    require(
        isinstance(example["graft_event_id"], int) and example["graft_event_id"] > 0, "event id"
    )
    require(example["graft_event_version"] == 1, "event version")
    require(example["graft_contract_version"] == "v1", "event contract version")
    require(isinstance(example["graft_payload"], dict), "event payload")


def check_openapi(document: dict[str, Any]) -> None:
    require(document.get("openapi") == "3.1.0", "OpenAPI 3.1 is required")
    paths = document.get("paths")
    if not isinstance(paths, dict):
        raise AssertionError("OpenAPI paths are required")
    operations: set[str] = set()
    for path, item in paths.items():
        require(path.startswith("/v1/"), f"non-versioned path: {path}")
        if not isinstance(item, dict):
            raise AssertionError(f"path item is not an object: {path}")
        for method, operation in item.items():
            if method not in {"get", "post", "put", "delete", "patch"}:
                continue
            if not isinstance(operation, dict):
                raise AssertionError(f"operation is not an object: {path} {method}")
            operation_id = operation.get("operationId")
            require(isinstance(operation_id, str), f"operationId missing: {path} {method}")
            if not isinstance(operation_id, str):
                raise AssertionError(f"operationId is not a string: {path} {method}")
            operations.add(operation_id)
            responses = operation.get("responses", {})
            require(
                "200" in responses or "201" in responses or "202" in responses,
                f"success response missing: {operation_id}",
            )
            require("default" not in responses, f"default response hides errors: {operation_id}")
    require(operations == OPERATIONS, f"operation set mismatch: {operations}")
    declared_codes: set[str] = set()
    for item in paths.values():
        if not isinstance(item, dict):
            continue
        for operation in item.values():
            if not isinstance(operation, dict) or "operationId" not in operation:
                continue
            codes = operation.get("x-graft-declared-error-codes")
            require(
                isinstance(codes, list),
                f"declared error mapping missing: {operation['operationId']}",
            )
            if not isinstance(codes, list) or not all(isinstance(code, str) for code in codes):
                raise AssertionError(
                    f"declared error mapping is not a string list: {operation['operationId']}"
                )
            declared_codes.update(codes)
            for code in codes:
                require(code in ERROR_CODES, f"unknown declared error code: {code}")
    require(declared_codes == ERROR_CODES, "REST standard error model is incomplete")
    components = document.get("components", {})
    require(isinstance(components, dict), "OpenAPI components are required")
    schemas_value = components.get("schemas", {})
    require(isinstance(schemas_value, dict), "OpenAPI schemas are required")
    schemas: dict[str, Any] = schemas_value
    required_schemas = {
        "RunCreateRequest",
        "Run",
        "RunEvent",
        "EventReplayPage",
        "CancelOutcome",
        "ErrorEnvelope",
        "ExternalReference",
    }
    require(required_schemas <= schemas.keys(), "required OpenAPI schemas are missing")
    versioning = document.get("x-graft-versioning", {})
    require(isinstance(versioning.get("rule"), str), "additive-versioning rule is missing")
    require(
        isinstance(versioning.get("breaking-change"), str), "breaking-versioning rule is missing"
    )
    examples_value = components.get("examples", {})
    require(isinstance(examples_value, dict), "OpenAPI examples are required")
    examples: dict[str, Any] = examples_value
    require(
        "CreateRunRequest" in examples and "Run" in examples and "EventReplayPage" in examples,
        "operation examples missing",
    )
    for name in ("CreateRunRequest", "Run", "EventReplayPage", "CancelRequest", "CancelOutcome"):
        require(
            name in examples and isinstance(examples[name].get("value"), dict),
            f"invalid example: {name}",
        )
    for code in ERROR_CODES:
        example = examples.get(_error_example_name(code), {}).get("value")
        require(isinstance(example, dict), f"missing error example: {code}")
        validate_error(example, code)
    for schema_name in required_schemas:
        properties = schemas[schema_name].get("properties", {})
        require(isinstance(properties, dict), f"schema properties missing: {schema_name}")
        # Protocol metadata (status, type, properties, etc.) is not a domain
        # identifier.  Domain IDs and externally owned references are graft_*.
        for field_name in properties:
            if field_name.endswith("_id") or field_name.endswith("_ref"):
                require(field_name.startswith("graft_"), f"unprefixed domain field {field_name}")

    try:
        jsonschema = importlib.import_module("jsonschema")
        resolver = jsonschema.RefResolver.from_schema(
            document,
            store={
                "https://graft.example/contracts/run-events-v1.schema.json": load(
                    "run-events-v1.schema.json"
                )
            },
        )
        validator = jsonschema.Draft202012Validator(document, resolver=resolver)
        schema_examples = {
            "CreateRunRequest": "RunCreateRequest",
            "Run": "Run",
            "EventReplayPage": "EventReplayPage",
            "CancelRequest": "CancelRequest",
            "CancelOutcome": "CancelOutcome",
        }
        for example_name, schema_name in schema_examples.items():
            value = examples[example_name]["value"]
            validator = jsonschema.Draft202012Validator(
                {"$ref": f"#/components/schemas/{schema_name}"}, resolver=resolver
            )
            validator.validate(value)
        for name, example in examples.items():
            if name in schema_examples:
                continue
            validator = jsonschema.Draft202012Validator(
                {"$ref": "#/components/schemas/ErrorEnvelope"}, resolver=resolver
            )
            validator.validate(example["value"])
    except ImportError:
        return


def _pointer(document: dict[str, Any], reference: str) -> Any:
    value: Any = document
    for part in reference.removeprefix("#/").split("/"):
        value = value[part.replace("~1", "/").replace("~0", "~")]
    return value


def _schema_signature(
    schema: Any,
    documents: dict[str, dict[str, Any]] | None = None,
    resolving: tuple[str, ...] = (),
) -> Any:
    """Return a complete semantic schema signature, including nested refs/items.

    Descriptions are deliberately retained: changing a field's documented
    meaning is a contract change even when its JSON type remains unchanged.
    Local and checked-in external references are expanded so a nested schema
    cannot be changed behind an apparently stable ``$ref``.
    """

    if isinstance(schema, list):
        return [_schema_signature(item, documents, resolving) for item in schema]
    if not isinstance(schema, dict):
        return schema
    reference = schema.get("$ref")
    if isinstance(reference, str) and documents is not None and reference.startswith("#/"):
        document = documents.get("__root__")
        if document is not None and reference not in resolving:
            return _schema_signature(
                _pointer(document, reference), documents, (*resolving, reference)
            )
    if isinstance(reference, str) and documents is not None and "#" in reference:
        document_name, fragment = reference.split("#", 1)
        document = documents.get(document_name)
        if document is not None and fragment and reference not in resolving:
            return _schema_signature(
                _pointer(document, f"#{fragment}"), documents, (*resolving, reference)
            )
    result: dict[str, Any] = {}
    for key in sorted(schema):
        if key == "$id":
            continue
        if key == "required" and isinstance(schema[key], list):
            result[key] = sorted(schema[key])
        else:
            result[key] = _schema_signature(schema[key], documents, resolving)
    return result


def _legacy_schema_signature(schema: dict[str, Any]) -> dict[str, Any]:
    """Retain the compact v1 baseline view alongside the expanded signature."""

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        properties = {}
    signature: dict[str, Any] = {
        "required": sorted(schema.get("required", [])),
        "properties": {},
    }
    for name, value in properties.items():
        if not isinstance(value, dict):
            signature["properties"][name] = value
            continue
        signature["properties"][name] = {
            key: value[key]
            for key in (
                "type",
                "const",
                "enum",
                "pattern",
                "minimum",
                "maximum",
                "minLength",
                "maxLength",
                "format",
            )
            if key in value
        }
    for key in ("type", "additionalProperties", "not"):
        if key in schema:
            signature[key] = schema[key]
    for name, value in properties.items():
        if isinstance(value, dict) and isinstance(value.get("additionalProperties"), dict):
            signature["properties"][name]["additionalProperties"] = value["additionalProperties"]
    return signature


def _legacy_input_signature(schema: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "required": sorted(schema.get("required", [])),
        "properties": {},
    }
    for name, value in schema.get("properties", {}).items():
        if not isinstance(value, dict):
            continue
        result["properties"][name] = {
            key: value[key]
            for key in ("type", "const", "enum", "minimum", "maximum", "minLength", "maxLength")
            if key in value
        }
    if "not" in schema:
        result["not"] = schema["not"]
    return result


def _input_signature(schema: dict[str, Any], documents: dict[str, dict[str, Any]]) -> Any:
    """Capture the complete MCP input schema, not just top-level primitives."""

    return _schema_signature(schema, documents)


def _current_compatibility_signature(
    openapi: dict[str, Any], event_schema: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    components = openapi["components"]
    schemas = components["schemas"]
    documents = {
        "__root__": openapi,
        "https://graft.example/contracts/harness-v1.openapi.json": openapi,
        "https://graft.example/contracts/run-events-v1.schema.json": event_schema,
    }
    rest_operations: list[dict[str, Any]] = []
    for path, item in openapi["paths"].items():
        for method, operation in item.items():
            if method not in {"get", "post", "put", "delete", "patch"}:
                continue
            rest_operations.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "operationId": operation["operationId"],
                    "parameters": _schema_signature(
                        [*item.get("parameters", []), *operation.get("parameters", [])], documents
                    ),
                    "requestBody": _schema_signature(operation.get("requestBody", {}), documents),
                    "responses": _schema_signature(operation.get("responses", {}), documents),
                    "security": _schema_signature(
                        operation.get("security", openapi.get("security", [])), documents
                    ),
                    "provider_status": operation.get("x-graft-provider-status"),
                    "provider_supported_errors": sorted(
                        operation.get("x-graft-provider-supported-errors", [])
                    ),
                }
            )
    return {
        "rest": {
            "operations": sorted(
                (operation["method"], operation["path"], operation["operationId"])
                for operation in rest_operations
            ),
            "operation_contracts": {
                f"{operation['method']} {operation['path']}": operation
                for operation in rest_operations
            },
            "operation_details": {
                operation["operationId"]: operation for operation in rest_operations
            },
            "schemas": {
                name: _legacy_schema_signature(schemas[name])
                for name in (
                    "AlertTrigger",
                    "RunCreateRequest",
                    "Run",
                    "EventReplayPage",
                    "CancelRequest",
                    "CancelOutcome",
                    "ErrorEnvelope",
                )
            },
            "schema_details": {
                name: _schema_signature(schemas[name], documents) for name in schemas
            },
            "replay_uri": "/v1/runs/{graft_run_id}/events",
            "cursor": "after_graft_event_id exclusive",
            "idempotency": "X-Graft-Idempotency-Key required for create",
        },
        "events": {
            "required": sorted(event_schema["required"]),
            "event_types": sorted(event_schema["properties"]["graft_event_type"]["x-known-values"]),
            "payloads": {
                name: _legacy_schema_signature(value)
                for name, value in event_schema["$defs"].items()
                if name.endswith("Payload")
            },
            "payload_details": {
                name: _schema_signature(value, {"__root__": event_schema})
                for name, value in event_schema["$defs"].items()
                if name.endswith("Payload")
            },
            "cursor": "after_graft_event_id exclusive",
        },
        "mcp": {
            "transport": manifest["transport"],
            "tools": {
                tool["name"]: {
                    "operation": tool["x-graft-authority-operation"],
                    "rest": tool["x-graft-rest-operation"],
                    "input": _legacy_input_signature(tool["inputSchema"]),
                    "output": tool["outputSchema"],
                    "input_schema": _input_signature(tool["inputSchema"], documents),
                    "output_schema": _schema_signature(tool["outputSchema"], documents),
                    "error_codes": sorted(tool["x-graft-error-codes"]),
                    "idempotency": tool["x-graft-idempotency"],
                    "cursor": tool["x-graft-cursor"],
                }
                for tool in manifest["tools"]
            },
            "resources": sorted(resource["uri"] for resource in manifest["resources"]),
            "resource_details": [
                _schema_signature(resource, documents) for resource in manifest["resources"]
            ],
        },
    }


def _diff_compatibility(baseline: Any, current: Any, path: str = "") -> list[str]:
    """Report breaking changes while allowing policy-approved additions.

    Additions are not uniformly safe.  The event envelope and non-sensitive
    payloads are tolerant, but pointer/reference payloads and existing MCP
    Tool/Resource declarations are closed security boundaries.  This keeps a
    raw result field from being misclassified as an ordinary optional field.
    """

    if isinstance(baseline, dict) and isinstance(current, dict):
        failures: list[str] = []
        for key, expected in baseline.items():
            if key not in current:
                failures.append(f"removed {path}/{key}")
            else:
                failures.extend(_diff_compatibility(expected, current[key], f"{path}/{key}"))
        for key in current.keys() - baseline.keys():
            if _closed_addition(path, key, current[key]):
                failures.append(f"closed additive field {path}/{key}")
        return failures
    if isinstance(baseline, list) and isinstance(current, list):
        baseline_values = [list(value) if isinstance(value, tuple) else value for value in baseline]
        current_values = [list(value) if isinstance(value, tuple) else value for value in current]
        if path.endswith("/required"):
            return [] if set(current_values) == set(baseline_values) else [f"changed {path}"]
        if path.endswith("/event_types"):
            return [] if set(baseline_values) <= set(current_values) else [f"removed {path}"]
        if path.endswith("/enum"):
            return [] if baseline_values == current_values else [f"changed {path}"]
        if path.endswith("/operations"):
            return (
                []
                if all(value in current_values for value in baseline_values)
                else [f"removed {path}"]
            )
        if path.endswith("/resource_details"):
            return (
                []
                if all(value in current_values for value in baseline_values)
                else [f"removed {path}"]
            )
        # Resource templates are keyed in the current signature, but retain
        # this rule for older baselines and fixture compatibility.
        if path.endswith("/resources"):
            return [] if set(baseline_values) <= set(current_values) else [f"removed {path}"]
        return [] if baseline_values == current_values else [f"changed {path}"]
    if isinstance(baseline, list) and isinstance(current, dict) and path.endswith("/resources"):
        return [] if set(baseline) <= set(current) else [f"removed {path}"]
    if baseline != current:
        return [f"changed {path}: {baseline!r} -> {current!r}"]
    return []


def _closed_addition(path: str, key: str, value: Any) -> bool:
    """Return whether a newly added key violates a closed v1 boundary."""

    normalised = path.lower()
    key_lower = key.lower()
    # All named artifact/reference payload variants, including nested external
    # reference metadata, are closed.  Their reviewed pointer metadata is
    # represented in the baseline and therefore still requires an explicit
    # schema/baseline review to change.
    if key_lower == "graft_pointer_metadata":
        pointer_payload_path = any(
            f"/events/{location}/{payload_name}/" in normalised
            for location in ("payload_details", "payloads")
            for payload_name in (
                "pointerpayload",
                "toolcallresultpayload",
                "evidencepayload",
            )
        )
        return not (pointer_payload_path and _is_safe_pointer_metadata_schema(value))
    if _is_closed_pointer_reference_path(normalised, key_lower):
        return True
    # Existing MCP declarations are closed.  New entries are represented by
    # additions to /mcp/tools or /mcp/resource_details and remain additive;
    # only the explicitly reviewed extension metadata key is safe on an
    # existing declaration.
    if "/mcp/tools/" in normalised or "/mcp/resource_details/" in normalised:
        # REST and MCP share ordinary output schemas.  An optional field added
        # under a schema's ``properties`` is therefore forward-compatible,
        # but only after the closed pointer/reference shapes above have been
        # excluded.  The declaration itself remains closed.
        if "/output_schema/" in normalised and _ends_at_properties(normalised):
            return False
        if key_lower in {"x-graft-extension-metadata", "extension_metadata"}:
            return not _is_safe_pointer_metadata_schema(value)
        return True
    return "/output_schema" in normalised


def _is_closed_pointer_reference_path(path: str, key: str) -> bool:
    """Recognise additions inside reviewed pointer/reference shapes.

    Expanded ``$ref`` signatures do not always retain the source schema name.
    In particular, an ``ExternalReference`` nested in ``Run`` is represented
    by its field path.  Check both named definitions and those semantic field
    names so an ordinary shared output field can be additive without opening a
    pointer/reference boundary.
    """

    segments = {segment for segment in path.split("/") if segment}
    closed_payload_names = {
        "pointerpayload",
        "toolcallresultpayload",
        "evidencepayload",
        "externalreference",
    }
    closed_reference_fields = {
        "graft_ref",
        "graft_artifact_ref",
        "graft_external_ref",
        "graft_finding_ref",
    }
    return bool(
        segments & closed_payload_names
        or segments & closed_reference_fields
        or key in closed_reference_fields
    )


def _ends_at_properties(path: str) -> bool:
    """Return whether an addition is a schema property, not schema metadata."""

    return path.rsplit("/", 1)[-1] == "properties"


def _is_safe_pointer_metadata_schema(value: Any) -> bool:
    """Recognise the one reviewed pointer metadata extension shape."""

    if not isinstance(value, dict):
        return False
    return value == {
        "additionalProperties": False,
        "properties": {
            "graft_label": {"maxLength": 256, "type": "string"},
            "graft_origin": {"maxLength": 256, "type": "string"},
        },
        "type": "object",
    } or value == {
        "additionalProperties": False,
        "description": (
            "The only reviewed v1 extension point for pointer metadata; it carries "
            "labels, never content."
        ),
        "properties": {
            "graft_label": {"maxLength": 256, "type": "string"},
            "graft_origin": {"maxLength": 256, "type": "string"},
        },
        "type": "object",
    }


def check_compatibility_baseline(
    openapi: dict[str, Any], event_schema: dict[str, Any], manifest: dict[str, Any]
) -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    require(isinstance(baseline, dict), "compatibility baseline must be an object")
    current = _current_compatibility_signature(openapi, event_schema, manifest)
    failures = _diff_compatibility(baseline, current, "contract")
    require(not failures, "breaking contract drift: " + "; ".join(failures))


def _error_example_name(code: str) -> str:
    return {
        "authentication_required": "AuthenticationRequired",
        "authentication_failed": "AuthenticationFailed",
        "authorisation_denied": "AuthorisationDenied",
        "invalid_request": "InvalidRequest",
        "unsupported_contract_version": "UnsupportedContractVersion",
        "not_found": "NotFound",
        "idempotency_conflict": "IdempotencyConflict",
        "state_conflict": "StateConflict",
        "cursor_invalid": "CursorInvalid",
        "replay_cursor_expired": "ReplayCursorExpired",
        "throttled": "Throttled",
        "request_timeout": "RequestTimeout",
        "service_unavailable": "ServiceUnavailable",
        "internal_error": "InternalError",
    }[code]


def _mcp_to_rest_operation(operation: str) -> str:
    return {
        "create_run": "createRun",
        "get_run": "getRun",
        "cancel_run": "cancelRun",
        "replay_run_events": "replayRunEvents",
    }[operation]


def check_events(document: dict[str, Any]) -> None:
    properties = document.get("properties", {})
    require(document.get("$schema", "").endswith("draft/2020-12/schema"), "event schema draft")
    require(properties.get("graft_event_version", {}).get("const") == 1, "event version schema")
    known = set(properties.get("graft_event_type", {}).get("x-known-values", []))
    require(known == EVENT_TYPES, f"event taxonomy mismatch: {known ^ EVENT_TYPES}")
    payload_defs = document.get("$defs", {})
    require(
        payload_defs.get("PointerPayload", {}).get("additionalProperties") is False,
        "pointer payload must be closed",
    )
    require(
        payload_defs.get("ToolCallResultPayload", {}).get("additionalProperties") is False,
        "tool-call result payload must be closed",
    )
    require(
        payload_defs.get("EvidencePayload", {}).get("additionalProperties") is False,
        "evidence payload must be closed",
    )
    require(
        payload_defs.get("ExternalReference", {}).get("additionalProperties") is False,
        "external references must be closed",
    )
    pointer_metadata = payload_defs.get("PointerMetadata", {})
    require(
        pointer_metadata.get("additionalProperties") is False,
        "pointer metadata extension must be closed",
    )
    for payload_name in ("PointerPayload", "ToolCallResultPayload", "EvidencePayload"):
        properties = payload_defs[payload_name].get("properties", {})
        require(
            set(properties)
            <= {
                "graft_ref",
                "graft_artifact_ref",
                "graft_tool_call_id",
                "graft_evidence_id",
                "graft_external_ref",
                "graft_pointer_metadata",
            },
            f"{payload_name} contains an unreviewed field",
        )
    require(
        set(payload_defs["StatusPayload"]["properties"]["graft_status"]["enum"]) == RUN_STATUSES,
        "status enum is not aligned with the Python contract model",
    )
    require(
        set(payload_defs["DonePayload"]["properties"]["graft_outcome"]["enum"])
        == TERMINAL_OUTCOMES,
        "outcome enum is not aligned with the Python contract model",
    )
    require(
        set(payload_defs["ErrorPayload"]["properties"]["graft_code"]["enum"]) == ERROR_CODES,
        "event error-code enum is not aligned with the Python contract model",
    )
    examples = document.get("examples", [])
    require(isinstance(examples, list), "event examples must be an array")
    by_type = {example.get("graft_event_type") for example in examples if isinstance(example, dict)}
    require(by_type >= EVENT_TYPES, f"missing event examples: {EVENT_TYPES - by_type}")
    for example in examples:
        require(isinstance(example, dict), "event example must be an object")
        validate_event(example)
    try:
        Draft202012Validator = importlib.import_module("jsonschema").Draft202012Validator
    except ImportError:
        return
    validator = Draft202012Validator(document)
    for example in examples:
        validator.validate(example)


def check_mcp(schema: dict[str, Any], manifest: dict[str, Any]) -> None:
    require(manifest.get("graft_manifest_version") == "v1", "MCP manifest version")
    require(
        set(manifest.get("capabilities", {})) == {"tools", "resources"},
        "MCP tools/resources capabilities",
    )
    require(
        manifest.get("authentication", {}).get("required") is True,
        "MCP authentication must be declared required",
    )
    require(
        manifest.get("authentication", {}).get("status") == "placeholder-required",
        "MCP auth status",
    )
    require(manifest.get("transport") == "streamable-http", "MCP transport must be streamable HTTP")
    compatibility = manifest.get("compatibility", {})
    additive_rules = compatibility.get("additive_rules", "").lower()
    require(
        "new tool or resource entries" in additive_rules,
        "MCP additive policy must name new Tool/Resource entries",
    )
    require(
        "not open-ended additive" in additive_rules,
        "MCP additive policy must close existing Tool/Resource shapes",
    )
    require(
        "pointer/reference" in compatibility.get("pointer_reference_policy", "").lower(),
        "MCP pointer/reference policy is missing",
    )
    require(
        "graft_pointer_metadata" in compatibility.get("pointer_reference_policy", "").lower(),
        "MCP pointer metadata extension policy is missing",
    )
    mcp_defs = schema.get("$defs", {})
    require(mcp_defs.get("Tool", {}).get("additionalProperties") is False, "MCP Tool is open")
    require(
        mcp_defs.get("Resource", {}).get("additionalProperties") is False,
        "MCP Resource is open",
    )
    tools = manifest.get("tools", [])
    require(
        {tool.get("x-graft-authority-operation") for tool in tools}
        == {"create_run", "get_run", "cancel_run", "replay_run_events"},
        "MCP tool parity",
    )
    require(
        all(tool.get("name", "").startswith("graft_") for tool in tools),
        "MCP tools must be graft-owned",
    )
    resources = manifest.get("resources", [])
    require(
        {resource.get("uri") for resource in resources}
        == {"graft://runs/{graft_run_id}", "graft://runs/{graft_run_id}/events"},
        "MCP resource URI templates",
    )
    require(
        not any("grafana" in json.dumps(value).lower() for value in tools + resources),
        "MCP manifest must not contain Grafana fields",
    )
    require(
        schema.get("$defs", {})
        .get("Tool", {})
        .get("properties", {})
        .get("x-graft-authority-operation"),
        "MCP schema tool operation enum",
    )
    rest = load("harness-v1.openapi.json")
    semantic_documents = {
        "__root__": rest,
        "https://graft.example/contracts/harness-v1.openapi.json": rest,
        "https://graft.example/contracts/run-events-v1.schema.json": load(
            "run-events-v1.schema.json"
        ),
    }
    rest_by_operation = {
        operation["operationId"]: (
            method.upper(),
            path,
            {
                **operation,
                "parameters": [
                    *item.get("parameters", []),
                    *operation.get("parameters", []),
                ],
            },
        )
        for path, item in rest["paths"].items()
        for method, operation in item.items()
        if isinstance(operation, dict) and "operationId" in operation
    }
    for tool in tools:
        method, path, operation = rest_by_operation[
            _mcp_to_rest_operation(tool["x-graft-authority-operation"])
        ]
        require(
            tool["x-graft-rest-operation"] == f"{method} {path}",
            f"MCP REST mapping drift: {tool['name']}",
        )
        response_codes = _response_error_codes(operation, rest)
        require(
            response_codes == set(operation.get("x-graft-declared-error-codes", [])),
            f"REST response error mapping drift: {tool['name']}",
        )
        require(
            set(tool["x-graft-provider-supported-errors"])
            == set(operation.get("x-graft-provider-supported-errors", [])),
            f"MCP provider error mapping drift: {tool['name']}",
        )
        require(
            set(operation.get("x-graft-declared-error-codes", []))
            == set(tool["x-graft-error-codes"]),
            f"MCP declared error mapping drift: {tool['name']}",
        )
        success_schema = _success_response_schema(operation)
        require(
            _schema_signature(tool["outputSchema"], semantic_documents)
            == _schema_signature(success_schema, semantic_documents),
            f"MCP output schema mapping drift: {tool['name']}",
        )
        _check_mcp_input_parity(tool, operation, semantic_documents)
    try:
        Draft202012Validator = importlib.import_module("jsonschema").Draft202012Validator
    except ImportError:
        return
    manifest_for_validation = dict(manifest)
    manifest_for_validation.pop("$schema", None)
    manifest_for_validation.pop("$id", None)
    Draft202012Validator(schema).validate(manifest_for_validation)
    examples = schema.get("examples", [])
    require(isinstance(examples, list) and len(examples) >= 8, "MCP examples are required")
    openapi = rest
    try:
        jsonschema = importlib.import_module("jsonschema")
        store = {
            "https://graft.example/contracts/harness-v1.openapi.json": openapi,
            "https://graft.example/contracts/run-events-v1.schema.json": load(
                "run-events-v1.schema.json"
            ),
        }
        resolver = jsonschema.RefResolver.from_schema(openapi, store=store)
        tools_by_name = {tool["name"]: tool for tool in manifest["tools"]}
        event_schema = store["https://graft.example/contracts/run-events-v1.schema.json"]
        error_schema = {"$ref": "#/components/schemas/ErrorEnvelope"}
        resource_templates = {resource["uri"] for resource in resources}
        for example in examples:
            method = example.get("method")
            if method == "tools/call":
                params = example.get("params", {})
                tool = tools_by_name.get(params.get("name"))
                require(tool is not None, f"MCP example names unknown tool: {params.get('name')}")
                if tool is None:
                    continue
                jsonschema.Draft202012Validator(tool["inputSchema"], resolver=resolver).validate(
                    params.get("arguments", {})
                )
                continue
            if method == "tools/call/result":
                params = example.get("params", {})
                tool = tools_by_name.get(params.get("name"))
                require(tool is not None, f"MCP result names unknown tool: {params.get('name')}")
                if tool is None:
                    continue
                jsonschema.Draft202012Validator(tool["outputSchema"], resolver=resolver).validate(
                    example.get("result")
                )
                continue
            if method == "tools/call/error":
                params = example.get("params", {})
                require(params.get("name") in tools_by_name, "MCP error names unknown tool")
                _validate_mcp_protocol_error(example, error_schema, jsonschema, resolver)
                continue
            if method == "resources/read":
                uri = example.get("params", {}).get("uri")
                require(
                    isinstance(uri, str) and _matches_resource_template(uri, resource_templates),
                    f"MCP resource URI is not declared: {uri}",
                )
                continue
            if method == "resources/read/result":
                _validate_mcp_resource_result(example, resource_templates, resolver, jsonschema)
                continue
            if "graft_event_type" in example:
                jsonschema.Draft202012Validator(event_schema).validate(example)
                continue
            if "code" in example and "message" in example:
                _validate_mcp_protocol_error(example, error_schema, jsonschema, resolver)
                continue
            raise AssertionError(f"unclassified MCP example: {example}")
    except ImportError:
        return


def _matches_resource_template(uri: str, templates: set[str]) -> bool:
    return any(
        uri.startswith(template.split("{", 1)[0]) and uri.endswith(template.split("}", 1)[1])
        for template in templates
    )


def _validate_mcp_protocol_error(
    example: dict[str, Any], error_schema: dict[str, Any], jsonschema: Any, resolver: Any
) -> None:
    error = example.get("error", example)
    require(isinstance(error, dict), "MCP protocol error object")
    require(isinstance(error.get("code"), int), "MCP protocol error code")
    require(isinstance(error.get("message"), str), "MCP protocol error message")
    jsonschema.Draft202012Validator(error_schema, resolver=resolver).validate(error.get("data"))


def _success_response_schema(operation: dict[str, Any]) -> Any:
    for status in ("200", "201", "202"):
        response = operation.get("responses", {}).get(status)
        if isinstance(response, dict):
            content = response.get("content", {})
            application_json = content.get("application/json")
            if isinstance(application_json, dict):
                return application_json.get("schema")
    raise AssertionError(f"operation has no JSON success schema: {operation.get('operationId')}")


def _resolved_schema(schema: Any, documents: dict[str, dict[str, Any]]) -> Any:
    if not isinstance(schema, dict):
        return schema
    reference = schema.get("$ref")
    if not isinstance(reference, str):
        return schema
    if reference.startswith("#/"):
        return _pointer(documents["__root__"], reference)
    if "#" in reference:
        document_name, fragment = reference.split("#", 1)
        return _pointer(documents[document_name], f"#{fragment}")
    return schema


def _response_error_codes(operation: dict[str, Any], document: dict[str, Any]) -> set[str]:
    codes: set[str] = set()
    for status, response in operation.get("responses", {}).items():
        if str(status).startswith("2"):
            continue
        resolved = response
        if isinstance(response, dict) and isinstance(response.get("$ref"), str):
            resolved = _pointer(document, response["$ref"])
        require(
            isinstance(resolved, dict) and isinstance(resolved.get("x-graft-error-codes"), list),
            f"response {status} has no canonical error mapping: {operation.get('operationId')}",
        )
        codes.update(resolved["x-graft-error-codes"])
    return codes


def _check_mcp_input_parity(
    tool: dict[str, Any], operation: dict[str, Any], documents: dict[str, dict[str, Any]]
) -> None:
    schema = tool["inputSchema"]
    operation_id = operation["operationId"]
    required = set(schema.get("required", []))
    properties = schema.get("properties", {})
    require("graft_contract_version" in properties, f"MCP version missing: {tool['name']}")
    require(
        isinstance(properties, dict) and isinstance(schema.get("type"), str),
        f"MCP input schema is malformed: {tool['name']}",
    )
    rest_parameters = operation.get("parameters", [])
    require(isinstance(rest_parameters, list), f"REST parameters are malformed: {tool['name']}")
    rest_parameters = [_resolved_schema(parameter, documents) for parameter in rest_parameters]
    path_parameters = {
        parameter["name"]: parameter["schema"]
        for parameter in rest_parameters
        if isinstance(parameter, dict)
        and parameter.get("in") == "path"
        and isinstance(parameter.get("schema"), dict)
    }
    query_parameters = {
        parameter["name"]: parameter["schema"]
        for parameter in rest_parameters
        if isinstance(parameter, dict)
        and parameter.get("in") == "query"
        and isinstance(parameter.get("schema"), dict)
    }
    expected_names = set(path_parameters) | set(query_parameters)
    request_body = operation.get("requestBody", {})
    if isinstance(request_body, dict):
        content = request_body.get("content", {})
        application_json = content.get("application/json", {}) if isinstance(content, dict) else {}
        body_schema = application_json.get("schema") if isinstance(application_json, dict) else None
        body_schema = _resolved_schema(body_schema, documents)
        if isinstance(body_schema, dict) and body_schema:
            body_properties = body_schema.get("properties", {})
            if isinstance(body_properties, dict):
                expected_names.update(body_properties)
            require(
                schema.get("additionalProperties") == body_schema.get("additionalProperties"),
                f"MCP body extension policy drift: {tool['name']}",
            )
            rest_required = set(body_schema.get("required", []))
            mcp_required = (
                required
                - set(path_parameters)
                - set(query_parameters)
                - {
                    "graft_contract_version",
                    "graft_idempotency_key",
                }
            )
            require(mcp_required == rest_required, f"MCP body requiredness drift: {tool['name']}")
            # Compare each REST body field semantically; the MCP envelope may
            # also carry path/query fields and the protocol version marker.
            for name, value in body_properties.items() if isinstance(body_properties, dict) else ():
                require(
                    _schema_signature(properties.get(name), documents)
                    == _schema_signature(value, documents),
                    f"MCP body field parity drift: {tool['name']} {name}",
                )
    for name, rest_schema in {**path_parameters, **query_parameters}.items():
        require(
            _schema_signature(properties.get(name), documents)
            == _schema_signature(rest_schema, documents),
            f"MCP parameter parity drift: {tool['name']} {name}",
        )
    require(
        expected_names <= set(properties) | {"graft_contract_version", "graft_idempotency_key"},
        f"MCP input omits REST fields: {tool['name']}",
    )
    if operation_id == "createRun":
        require({"graft_trigger", "graft_idempotency_key"} <= required, "MCP create parity")
        require(
            operation["parameters"][0]["$ref"].endswith("/IdempotencyKey"),
            "REST create idempotency parameter parity",
        )
        require(
            _schema_signature(properties["graft_idempotency_key"], documents)
            == _schema_signature(
                documents["__root__"]["components"]["parameters"]["IdempotencyKey"]["schema"],
                documents,
            ),
            "MCP idempotency header parity",
        )
    elif operation_id == "getRun":
        require(required == {"graft_run_id"}, "MCP get input parity")
    elif operation_id == "cancelRun":
        require(required == {"graft_run_id"}, "MCP cancel input parity")
        require(
            not any(
                "IdempotencyKey" in json.dumps(parameter) for parameter in operation["parameters"]
            ),
            "REST cancel idempotency parity",
        )
    elif operation_id == "replayRunEvents":
        require(required == {"graft_run_id"}, "MCP replay input parity")
        require(
            {"after_graft_event_id", "graft_event_limit", "graft_replay_mode"} <= properties.keys(),
            "MCP replay cursor/mode parity",
        )
        require("exclusive" in tool["x-graft-cursor"], "MCP exclusive cursor parity")


def _validate_mcp_resource_result(
    example: dict[str, Any],
    templates: set[str],
    resolver: Any,
    jsonschema: Any,
) -> None:
    uri = example.get("params", {}).get("uri")
    require(isinstance(uri, str) and _matches_resource_template(uri, templates), "MCP result URI")
    result = example.get("result")
    require(isinstance(result, dict) and isinstance(result.get("contents"), list), "MCP contents")
    if not isinstance(result, dict) or not isinstance(result.get("contents"), list):
        return
    for content in result["contents"]:
        require(
            isinstance(content, dict)
            and content.get("uri") == uri
            and content.get("mimeType") == "application/json"
            and isinstance(content.get("text"), str),
            "MCP resource content",
        )
        value = json.loads(content["text"])
        schema_name = "Run" if uri.count("/") == 3 else "EventReplayPage"
        jsonschema.Draft202012Validator(
            {"$ref": f"#/components/schemas/{schema_name}"}, resolver=resolver
        ).validate(value)


def check_compatibility_fixtures() -> None:
    additive = json.loads(
        (ROOT / "tests/fixtures/contract-additive.json").read_text(encoding="utf-8")
    )
    breaking = json.loads(
        (ROOT / "tests/fixtures/contract-breaking.json").read_text(encoding="utf-8")
    )
    require(
        additive["classification"] == "additive" and additive["consumer_action"] == "ignore",
        "additive fixture policy",
    )
    require(
        breaking["classification"] == "breaking" and breaking["ci_action"] == "fail",
        "breaking fixture policy",
    )
    require(
        additive["unknown_event_type"] not in EVENT_TYPES, "additive event fixture must be unknown"
    )
    require(breaking.get("mutations"), "breaking fixture must contain executable mutations")
    require(additive.get("mutations"), "additive fixture must contain executable mutations")
    require(
        any("PointerPayload" in mutation.get("path", "") for mutation in breaking["mutations"]),
        "breaking fixture must cover closed pointer payload additions",
    )
    require(
        any("mcp/tools/" in mutation.get("path", "") for mutation in breaking["mutations"]),
        "breaking fixture must cover existing MCP declaration additions",
    )


def check_fixture_mutations(
    openapi: dict[str, Any], event_schema: dict[str, Any], manifest: dict[str, Any]
) -> None:
    """Run the preserved compatibility fixtures against the real checker."""

    baseline = _current_compatibility_signature(openapi, event_schema, manifest)
    additive = json.loads(
        (ROOT / "tests/fixtures/contract-additive.json").read_text(encoding="utf-8")
    )
    breaking = json.loads(
        (ROOT / "tests/fixtures/contract-breaking.json").read_text(encoding="utf-8")
    )
    for mutation in additive["mutations"]:
        candidate = json.loads(json.dumps(baseline))
        _apply_mutation(candidate, mutation)
        require(not _diff_compatibility(baseline, candidate), "additive fixture was rejected")
    for mutation in breaking["mutations"]:
        candidate = json.loads(json.dumps(baseline))
        _apply_mutation(candidate, mutation)
        require(bool(_diff_compatibility(baseline, candidate)), "breaking fixture was accepted")


def _apply_mutation(document: dict[str, Any], mutation: dict[str, Any]) -> None:
    target: Any = document
    path = mutation["path"].strip("/").split("/")
    for part in path[:-1]:
        target = target[int(part)] if isinstance(target, list) else target[part]
    operation = mutation["operation"]
    key = path[-1]
    if operation == "remove":
        target.pop(int(key) if isinstance(target, list) else key)
    elif operation == "replace":
        target[int(key) if isinstance(target, list) else key] = mutation["value"]
    elif operation == "add":
        if isinstance(target, list):
            if key == "-" or int(key) == len(target):
                target.append(mutation["value"])
            else:
                target.insert(int(key), mutation["value"])
        else:
            target[key] = mutation["value"]
    else:
        raise AssertionError(f"unsupported fixture mutation: {operation}")


def main() -> int:
    try:
        openapi = load("harness-v1.openapi.json")
        events = load("run-events-v1.schema.json")
        mcp_schema = load("harness-mcp-v1.schema.json")
        manifest = load("harness-mcp-v1.manifest.json")
        check_openapi(openapi)
        check_events(events)
        check_mcp(mcp_schema, manifest)
        check_compatibility_fixtures()
        check_compatibility_baseline(openapi, events, manifest)
        check_fixture_mutations(openapi, events, manifest)
    except (AssertionError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"contract check failed: {exc}", file=sys.stderr)
        return 1
    print("contract check passed: REST, events, MCP, examples and compatibility fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
