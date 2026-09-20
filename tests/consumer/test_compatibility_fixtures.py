from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[2]


@pytest.mark.contract
def test_additive_fixture_is_accepted() -> None:
    fixture = json.loads((ROOT / "tests/fixtures/contract-additive.json").read_text())
    assert fixture["classification"] == "additive"
    assert fixture["consumer_action"] == "ignore"


@pytest.mark.contract
def test_breaking_fixture_is_rejected_by_policy() -> None:
    fixture = json.loads((ROOT / "tests/fixtures/contract-breaking.json").read_text())
    assert fixture["classification"] == "breaking"
    assert fixture["ci_action"] == "fail"


@pytest.mark.contract
def test_compatibility_fixtures_execute_against_expanded_signature() -> None:
    checker: Any = importlib.import_module("scripts.check_contracts")
    baseline = checker._current_compatibility_signature(
        checker.load("harness-v1.openapi.json"),
        checker.load("run-events-v1.schema.json"),
        checker.load("harness-mcp-v1.manifest.json"),
    )
    for name in ("contract-additive.json", "contract-breaking.json"):
        fixture = json.loads((ROOT / "tests/fixtures" / name).read_text())
        for mutation in fixture["mutations"]:
            candidate = json.loads(json.dumps(baseline))
            checker._apply_mutation(candidate, mutation)
            changes = checker._diff_compatibility(baseline, candidate, "contract")
            if fixture["classification"] == "additive":
                assert not changes
            else:
                assert changes


@pytest.mark.contract
def test_optional_run_output_field_propagates_to_mcp_create_and_get() -> None:
    checker: Any = importlib.import_module("scripts.check_contracts")
    baseline = checker._current_compatibility_signature(
        checker.load("harness-v1.openapi.json"),
        checker.load("run-events-v1.schema.json"),
        checker.load("harness-mcp-v1.manifest.json"),
    )
    fixture = json.loads((ROOT / "tests/fixtures/contract-additive.json").read_text())
    mutations = [
        mutation
        for mutation in fixture["mutations"]
        if "graft_optional_diagnostic" in mutation["path"]
    ]
    assert {mutation["path"] for mutation in mutations} == {
        "/rest/schemas/Run/properties/graft_optional_diagnostic",
        "/mcp/tools/graft_create_run/output_schema/properties/graft_optional_diagnostic",
        "/mcp/tools/graft_get_run/output_schema/properties/graft_optional_diagnostic",
    }

    candidate = json.loads(json.dumps(baseline))
    for mutation in mutations:
        checker._apply_mutation(candidate, mutation)

    optional_field = {"type": "string"}
    assert (
        candidate["rest"]["schemas"]["Run"]["properties"]["graft_optional_diagnostic"]
        == optional_field
    )
    for tool_name in ("graft_create_run", "graft_get_run"):
        assert (
            candidate["mcp"]["tools"][tool_name]["output_schema"]["properties"][
                "graft_optional_diagnostic"
            ]
            == optional_field
        )
    assert not checker._diff_compatibility(baseline, candidate, "contract")


@pytest.mark.contract
def test_closed_pointer_output_addition_remains_breaking() -> None:
    checker: Any = importlib.import_module("scripts.check_contracts")
    baseline = checker._current_compatibility_signature(
        checker.load("harness-v1.openapi.json"),
        checker.load("run-events-v1.schema.json"),
        checker.load("harness-mcp-v1.manifest.json"),
    )
    mutation = {
        "operation": "add",
        "path": (
            "/mcp/tools/graft_get_run/output_schema/properties/"
            "graft_finding_ref/anyOf/0/properties/graft_raw_result"
        ),
        "value": {"type": "string"},
    }
    candidate = json.loads(json.dumps(baseline))
    checker._apply_mutation(candidate, mutation)
    assert checker._diff_compatibility(baseline, candidate, "contract")
