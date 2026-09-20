from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[2]


def load(relative_path: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def validate(schema: dict[str, Any], value: object, *, root: dict[str, Any] | None = None) -> None:
    from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

    resolver = None
    if root is not None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from jsonschema.validators import RefResolver  # type: ignore[import-untyped]

            resolver = RefResolver.from_schema(
                root,
                store={
                    "https://graft.example/contracts/harness-v1.openapi.json": root,
                    "https://graft.example/contracts/run-events-v1.schema.json": load(
                        "contracts/run-events-v1.schema.json"
                    ),
                },
            )
    Draft202012Validator(schema, resolver=resolver).validate(value)


@pytest.mark.contract
def test_transport_independent_consumer_ignores_additive_fields_and_event_types() -> None:
    schema = load("contracts/run-events-v1.schema.json")
    event = {
        "graft_event_id": 1,
        "graft_run_id": "run-01",
        "graft_tenant_id": "tenant-01",
        "graft_event_type": "future_event_type",
        "graft_event_version": 1,
        "graft_payload": {
            "graft_future_field": {"graft_hint": "ignore"},
        },
        "graft_created_at": "2026-09-20T10:00:00Z",
        "graft_contract_version": "v1",
        "graft_future_envelope_field": True,
    }
    validate(schema, event)
    assert (
        event["graft_event_type"] not in schema["properties"]["graft_event_type"]["x-known-values"]
    )


@pytest.mark.contract
def test_transport_independent_consumer_requires_monotonic_exclusive_cursor() -> None:
    events = [{"graft_event_id": i} for i in range(1, 4)]
    after = 1
    assert [event["graft_event_id"] for event in events if event["graft_event_id"] > after] == [
        2,
        3,
    ]


@pytest.mark.contract
def test_transport_independent_consumer_accepts_all_success_shapes_and_cancellation_outcomes() -> (
    None
):
    openapi = load("contracts/harness-v1.openapi.json")
    examples = openapi["components"]["examples"]
    schemas = openapi["components"]["schemas"]
    for example_name, schema_name in (
        ("Run", "Run"),
        ("EventReplayPage", "EventReplayPage"),
        ("CancelOutcome", "CancelOutcome"),
    ):
        validate(schemas[schema_name], examples[example_name]["value"], root=openapi)

    cancel_schema = schemas["CancelOutcome"]
    for outcome in ("accepted", "already_requested", "already_terminal"):
        value = {
            **examples["CancelOutcome"]["value"],
            "graft_outcome": outcome,
        }
        validate(cancel_schema, value, root=openapi)


@pytest.mark.contract
def test_transport_independent_consumer_accepts_every_error_and_event_variant() -> None:
    openapi = load("contracts/harness-v1.openapi.json")
    error_schema = openapi["components"]["schemas"]["ErrorEnvelope"]
    error_examples = openapi["components"]["examples"]
    expected_errors = set(error_schema["properties"]["graft_code"]["enum"])
    actual_errors = {
        value["value"]["graft_code"]
        for value in error_examples.values()
        if isinstance(value, dict)
        and isinstance(value.get("value"), dict)
        and "graft_code" in value["value"]
    }
    assert actual_errors == expected_errors
    for value in error_examples.values():
        if (
            isinstance(value, dict)
            and isinstance(value.get("value"), dict)
            and "graft_code" in value["value"]
        ):
            validate(error_schema, value["value"])

    events = load("contracts/run-events-v1.schema.json")
    known = set(events["properties"]["graft_event_type"]["x-known-values"])
    examples_by_type = {value["graft_event_type"]: value for value in events["examples"]}
    assert set(examples_by_type) == known
    for value in examples_by_type.values():
        validate(events, value)


@pytest.mark.contract
def test_transport_independent_consumer_accepts_mcp_tools_resources_and_canonical_payloads() -> (
    None
):
    schema = load("contracts/harness-mcp-v1.schema.json")
    manifest = load("contracts/harness-mcp-v1.manifest.json")
    manifest_without_metadata = dict(manifest)
    manifest_without_metadata.pop("$schema", None)
    manifest_without_metadata.pop("$id", None)
    validate(schema, manifest_without_metadata)

    tools = {tool["name"]: tool for tool in manifest["tools"]}
    for example in schema["examples"]:
        method = example.get("method")
        if method == "tools/call":
            params = example["params"]
            validate(
                tools[params["name"]]["inputSchema"],
                params["arguments"],
                root=load("contracts/harness-v1.openapi.json"),
            )
        elif method == "tools/call/result":
            params = example["params"]
            validate(
                tools[params["name"]]["outputSchema"],
                example["result"],
                root=load("contracts/harness-v1.openapi.json"),
            )
        elif method == "resources/read/result":
            result = example["result"]
            assert result["contents"]
            for content in result["contents"]:
                assert content["mimeType"] == "application/json"
                json.loads(content["text"])
