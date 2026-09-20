from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.gate_0_3

ROOT = Path(__file__).parents[2]
REPORTER = ROOT / "deployment/gate-0.3/accepted_scope_reports.py"
WORKFLOW = ROOT / ".github/workflows/gate-0-3.yml"
REPORTS = ROOT / "specs/phase-1-walking-skeleton/evidence/dbos"
RECOVERY = ROOT / "deployment/gate-0.3/accepted_recovery.py"


def test_accepted_scope_report_set_is_canonical_and_complete() -> None:
    source = REPORTER.read_text()
    for name in (
        "01-async-mcp.json",
        "02-alive-silent.json",
        "03-listing.json",
        "04-versioning.json",
    ):
        assert name in source
    assert "DIAGNOSTIC_ONLY_WITH_ADR_0077_POLICY" not in source
    assert "ADR-0078" in source


def test_existing_canonical_evidence_is_machine_readable() -> None:
    expected = {
        "01-async-mcp.json",
        "02-alive-silent.json",
        "03-listing.json",
        "04-versioning.json",
    }
    assert {path.name for path in REPORTS.glob("*.json")} == expected
    values = {path.name: json.loads(path.read_text()) for path in REPORTS.glob("*.json")}
    assert all(value["verdict"] == "PASS" for value in values.values())
    async_actual = values["01-async-mcp.json"]["actual"]
    assert async_actual["runner_result"] == "passed"
    assert all(async_actual["assertions"].values())
    assert (
        async_actual["async_and_mcp_observations"]["async_dbos_steps"]["status"]["status"]
        == "SUCCESS"
    )
    assert (
        async_actual["async_and_mcp_observations"]["langgraph_no_checkpointer"][
            "checkpointer_configured"
        ]
        is False
    )
    assert async_actual["async_and_mcp_observations"]["langgraph_no_checkpointer"][
        "decorated_step_boundaries"
    ] == ["graph_step", "mcp_step", "mcp_failure_step"]
    assert (
        async_actual["async_and_mcp_observations"]["langgraph_no_checkpointer"]["result"][
            "mcp_failure"
        ]
        == "injected_failure:_MCPToolExecutionError"
    )
    assert (
        values["02-alive-silent.json"]["actual"]["assertions"][
            "wrong_executor_rejected_before_resume"
        ]
        is True
    )
    assert (
        values["02-alive-silent.json"]["actual"]["assertions"]["typed_durable_escalation_recorded"]
        is True
    )
    assert values["03-listing.json"]["actual"]["matching_count"] > 0
    assert all(values["03-listing.json"]["actual"]["assertions"].values())
    assert values["03-listing.json"]["actual"]["filter"] == {
        "api": "DBOS.list_workflows_async",
        "executor_id": "gate03-executor-a",
    }
    version_actual = values["04-versioning.json"]["actual"]
    assert all(version_actual["assertions"].values())
    observed = version_actual["observed_runtime_version_comparison"]
    assert observed["dbos_2_31_1"]["dbos_version"] == "2.31.1"
    assert observed["dbos_3_0_0"]["dbos_version"] == "3.0.0"
    assert observed["exact_difference"]["automatic_application_version_changed"] is True
    helper = observed["helper_only_false_compatible_observation"]
    assert helper["automatic_application_version_unchanged"] is True
    assert helper["workflow_result_changed"] is True
    assert helper["classification"] == "false-compatible observation, not compatibility behaviour"
    assert version_actual["policy_requirements_adr_0077"]["graft_compatibility_revision"]
    assert (
        version_actual["policy_requirements_adr_0077"]["graft_all_prior_cohort_drain_required"]
        is True
    )
    assert version_actual["policy_requirements_adr_0077"]["graft_drain_states"] == [
        "PENDING",
        "ENQUEUED",
        "DELAYED",
    ]
    assert values["04-versioning.json"]["public_api_only"] is False
    assert values["04-versioning.json"]["evidence_lanes"]["public_api_behaviour"] is False
    assert (
        "private DBOS runtime"
        in values["04-versioning.json"]["evidence_lanes"]["private_or_diagnostic_kinds"][0]
    )
    assert values["01-async-mcp.json"]["public_api_only"] is False
    assert values["02-alive-silent.json"]["public_api_only"] is False
    assert values["03-listing.json"]["public_api_only"] is False
    assert all(
        values[name]["evidence_lanes"]["private_or_diagnostic"]
        for name in (
            "01-async-mcp.json",
            "02-alive-silent.json",
            "03-listing.json",
            "04-versioning.json",
        )
    )
    assert "refusal" not in values["03-listing.json"]["expected"]
    assert "accepted requirements" in values["04-versioning.json"]["expected"]


def test_ci_does_not_require_deferred_cross_executor_research() -> None:
    workflow = WORKFLOW.read_text()
    assert "accepted_scope_reports.py all" in workflow
    assert "matrix_runner.py" not in workflow
    assert "recovery_race.py" not in workflow
    assert "test-2-result.json" not in workflow
    assert "test-3-result.json" not in workflow


def test_ci_retains_both_evidence_lanes_and_cleanup_can_read_env() -> None:
    workflow = WORKFLOW.read_text()
    assert "evidence/dbos/" in workflow
    assert "evidence/gate-0.3/" in workflow
    assert "retention-days: 14" in workflow
    compose = (ROOT / "deployment/gate-0.3/docker-compose.yml").read_text()
    assert "G03_APP_DB" in compose
    version_comparison = (ROOT / "deployment/gate-0.3/version_comparison.py").read_text()
    assert '"G03_APP_DB=gate03_app\\n"' in version_comparison
    assert '"G03_SYSTEM_DB=gate03_system\\n"' in version_comparison


def test_accepted_recovery_has_one_guard_and_durable_escalation_contract() -> None:
    source = RECOVERY.read_text()
    assert source.count("def accepted_runtime_recovery(") == 1
    assert "INSERT INTO gate03_accepted_run_metadata" in source
    assert "ON CONFLICT (graft_tenant_id, graft_run_id) DO NOTHING" in source
    assert "postgresql://gate03@localhost:56432/gate03_app" in source
    assert "SET LOCAL graft.tenant_id" in source
    assert "FORCE ROW LEVEL SECURITY" in source
    assert "graft_executor_id" in source
    assert "application_revision_mismatch" in source
    assert '"graft_resume_invoked": False' in source
    assert "gate03_operator_escalations" in source
    assert "ALIVE_BUT_SILENT" in source
    assert "AMBIGUOUS" in source
    assert "STUCK" in source
    assert "DBOSClient.resume_workflow" in source
    assert '"workflow_id": value.workflow_id' not in source
    assert '"executor_id": value.executor_id' not in source
    assert '"application_revision": value.application_revision' not in source


def test_accepted_recovery_evidence_retains_tenant_scope_probe() -> None:
    actual = json.loads(REPORTS.joinpath("02-alive-silent.json").read_text())["actual"]
    assert actual["graft_tenant_id"] == "graft-tenant-a"
    assert (
        actual["graft_tenant_scope_probe"]["graft_other_tenant_row_hidden_from_graft_tenant_a"]
        is True
    )
    assert (
        actual["graft_tenant_scope_probe"]["graft_other_tenant_row_visible_to_graft_tenant_b"]
        is True
    )


def test_accepted_recovery_report_contains_matching_revision_and_durable_records() -> None:
    value = json.loads(REPORTS.joinpath("02-alive-silent.json").read_text())
    actual = value["actual"]
    assert actual["run_metadata"]["insert_once"] is True
    assert actual["run_metadata"]["graft_conflicting_revision_rejected"] is True
    assert actual["assertions"]["wrong_executor_rejected_before_resume"] is True
    assert actual["assertions"]["graft_wrong_revision_rejected_before_resume"] is True
    assert actual["durable_escalation_record"]["not_stdout_only"] is True
    escalation = next(iter(actual["operator_escalations"].values()))["graft_durable_escalation"]
    assert "graft_state" in escalation
    assert "state" not in escalation
