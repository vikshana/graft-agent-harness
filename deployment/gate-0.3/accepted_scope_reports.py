#!/usr/bin/env python3
"""Emit the four canonical accepted-scope DBOS Gate 0.3 reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "specs/phase-1-walking-skeleton/evidence/dbos"
ACCEPTED_DECISION = "ADR-0078"
PYTHON_VERSION = "3.13.0"


def _command(command: list[str]) -> dict[str, object]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": _redact(completed.stdout),
        "stderr": _redact(completed.stderr),
    }


def _python_command(script: str, *arguments: str) -> list[str]:
    return [
        "uv",
        "run",
        "--locked",
        "--python",
        PYTHON_VERSION,
        "python",
        script,
        *arguments,
    ]


def _redact(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return value.replace("gate03_local_only", "[REDACTED]")
    return value


def _evidence(name: str) -> dict[str, object]:
    path = ROOT / "specs/phase-1-walking-skeleton/evidence/gate-0.3" / name
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _evidence_reference(name: str) -> dict[str, object]:
    path = ROOT / "specs/phase-1-walking-skeleton/evidence/gate-0.3" / name
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None,
    }


def _write(name: str, result: dict[str, object]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / name).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


def run(
    report: str,
    *,
    shared_experiment: tuple[dict[str, object], dict[str, object]] | None = None,
) -> int:
    started = datetime.now(UTC).isoformat()
    common = {
        "report": report,
        "started_at": started,
        "environment": {
            "python": platform.python_version(),
            "python_executable": sys.executable,
            "required_python": PYTHON_VERSION,
            "dbos": "3.0.0",
            "langgraph": "1.2.11 (locked)",
            "langchain_mcp_adapters": "0.3.2 (locked)",
            "mcp": "1.28.1 (locked)",
            "postgres": "16 pinned Gate 0.3 image",
            "pooler": "transaction-mode PgBouncer",
            "application_metadata_and_escalations": "transaction_mode_pgbouncer",
            "dbos_system_database": "direct_postgresql",
        },
        # These reports deliberately carry more than public behavioural API
        # observations.  Keep the public lane explicit instead of claiming
        # that source, schema, or application-owned SQL diagnostics are API
        # evidence.
        "public_api_only": False,
        "evidence_lanes": {
            "public_api_behaviour": True,
            "private_or_diagnostic": True,
            "private_or_diagnostic_kinds": [],
        },
        "private_dbos_api_or_system_table_mutation": False,
    }
    if report == "async-mcp":
        command = _python_command("deployment/gate-0.3/run_experiment.py", "run")
        if shared_experiment is None:
            outcome = _command(command)
            experiment = _evidence("result.json")
        else:
            experiment, outcome = shared_experiment
        result_value = experiment.get("result")
        g03_a = experiment.get("G03-A")
        async_step = g03_a.get("async_dbos_steps", {}) if isinstance(g03_a, dict) else {}
        langgraph = g03_a.get("langgraph_no_checkpointer", {}) if isinstance(g03_a, dict) else {}
        mcp = g03_a.get("streamable_http_mcp", {}) if isinstance(g03_a, dict) else {}
        graph_result = langgraph.get("result", {}) if isinstance(langgraph, dict) else {}
        async_assertions = {
            "async_step_result_is_success": isinstance(async_step, dict)
            and async_step.get("result") == "step:synthetic"
            and isinstance(async_step.get("status"), dict)
            and async_step["status"].get("status") == "SUCCESS",
            "langgraph_checkpointer_is_false": isinstance(langgraph, dict)
            and langgraph.get("checkpointer_configured") is False,
            "exact_decorated_dbos_steps": isinstance(langgraph, dict)
            and langgraph.get("decorated_step_boundaries")
            == ["graph_step", "mcp_step", "mcp_failure_step"],
            "real_mcp_successful_response": isinstance(graph_result, dict)
            and "mcp:synthetic" in str(graph_result.get("mcp"))
            and isinstance(mcp, dict)
            and mcp.get("capability") == "streamable_http_client_constructed",
            "expected_injected_failure": isinstance(graph_result, dict)
            and graph_result.get("mcp_failure") == "injected_failure:_MCPToolExecutionError",
        }
        result = {
            **common,
            "public_api_only": False,
            "evidence_lanes": {
                "public_api_behaviour": True,
                "private_or_diagnostic": True,
                "private_or_diagnostic_kinds": [
                    "DBOS runtime/source-version diagnostics in the retained experiment result"
                ],
            },
            "expected": (
                "async DBOS step, no-checkpointer LangGraph, real synthetic "
                "streamable-HTTP MCP and injected failure boundary"
            ),
            "actual": {
                "runner_result": result_value,
                "async_and_mcp_observations": g03_a,
                "assertions": async_assertions,
            },
            "command": outcome,
            "verdict": "PASS"
            if outcome["returncode"] == 0
            and result_value == "passed"
            and all(async_assertions.values())
            else "INCOMPLETE",
            "artefacts": [_evidence_reference("result.json")],
        }
        _write("01-async-mcp.json", result)
    elif report == "alive-silent":
        command = _python_command("deployment/gate-0.3/accepted_recovery.py", "run")
        outcome = _command(command)
        recovery = _json_stdout(outcome)
        result = {
            **common,
            "public_api_only": False,
            "evidence_lanes": {
                "public_api_behaviour": True,
                "private_or_diagnostic": True,
                "private_or_diagnostic_kinds": [
                    "application-owned metadata and escalation SQL is a disposable diagnostic lane"
                ],
            },
            "expected": (
                "matching executor identity and revision restart recovery; different "
                "executor automatic refusal; typed durable operator escalation for "
                "ambiguous/alive-silent/stuck"
            ),
            "actual": recovery,
            "command": outcome,
            "accepted_decision": ACCEPTED_DECISION,
            "verdict": "PASS"
            if outcome["returncode"] == 0 and recovery.get("verdict") == "PASS"
            else "INCOMPLETE",
            "artefacts": ["deployment/gate-0.3/accepted_recovery.py"],
        }
        _write("02-alive-silent.json", result)
    elif report == "listing":
        command = _python_command("deployment/gate-0.3/run_experiment.py", "run")
        if shared_experiment is None:
            outcome = _command(command)
            experiment = _evidence("result.json")
        else:
            experiment, outcome = shared_experiment
        listing = experiment.get("G03-C")
        listing_assertions = {
            "matching_executor_filter_is_exact": isinstance(listing, dict)
            and listing.get("filter")
            == {
                "api": "DBOS.list_workflows_async",
                "executor_id": "gate03-executor-a",
            }
            and listing.get("matching_executor_ids") == ["gate03-executor-a"],
            "matching_rows_are_present": isinstance(listing, dict)
            and int(listing.get("matching_count", 0)) > 0,
            "nonmatching_rows_are_excluded": isinstance(listing, dict)
            and int(listing.get("nonmatching_count", -1)) == 0,
            "negative_filter_query_is_exact": isinstance(listing, dict)
            and listing.get("negative_filter")
            == {
                "api": "DBOS.list_workflows_async",
                "executor_id": "does-not-exist",
            },
        }
        result = {
            **common,
            "public_api_only": False,
            "evidence_lanes": {
                "public_api_behaviour": True,
                "private_or_diagnostic": True,
                "private_or_diagnostic_kinds": [
                    "retained experiment includes runtime version/source diagnostics"
                ],
            },
            "expected": (
                "executor-filtered public listing through the supported DBOS client; "
                "recovery guard evidence is recorded separately by the accepted recovery report"
            ),
            "actual": (
                {**listing, "assertions": listing_assertions}
                if isinstance(listing, dict)
                else {"value": listing, "assertions": listing_assertions}
            ),
            "command": outcome,
            "verdict": "PASS"
            if outcome["returncode"] == 0 and all(listing_assertions.values())
            else "INCOMPLETE",
            "artefacts": [_evidence_reference("result.json")],
        }
        _write("03-listing.json", result)
    elif report == "versioning":
        command = _python_command("deployment/gate-0.3/version_comparison.py", "run")
        outcome = _command(command)
        comparison = _evidence("dbos-version-comparison-result.json")
        matrix = comparison.get("version_matrix", {})
        old_worker = (
            matrix.get("dbos_2_31_1", {}).get("3.13", {}).get("worker", {})
            if isinstance(matrix, dict)
            else {}
        )
        new_worker = (
            matrix.get("dbos_3_0_0", {}).get("3.13", {}).get("worker", {})
            if isinstance(matrix, dict)
            else {}
        )
        helper_comparison = comparison.get("helper_runtime_comparison", {})
        helper_baseline = (
            helper_comparison.get("baseline", {}).get("worker", {})
            if isinstance(helper_comparison, dict)
            else {}
        )
        helper_changed = (
            helper_comparison.get("changed", {}).get("worker", {})
            if isinstance(helper_comparison, dict)
            else {}
        )
        old_fields = old_worker.get("launch_runtime_application_version_fields", {})
        new_fields = new_worker.get("launch_runtime_application_version_fields", {})
        old_version = old_fields.get("GlobalParams", {}).get("app_version")
        new_version = new_fields.get("GlobalParams", {}).get("app_version")
        helper_old_version = (
            helper_baseline.get("launch_runtime_application_version_fields", {})
            .get("GlobalParams", {})
            .get("app_version")
            if isinstance(helper_baseline, dict)
            else None
        )
        helper_new_version = (
            helper_changed.get("launch_runtime_application_version_fields", {})
            .get("GlobalParams", {})
            .get("app_version")
            if isinstance(helper_changed, dict)
            else None
        )
        observed = {
            "dbos_2_31_1": {
                "dbos_version": old_worker.get("dbos_version"),
                "python": old_worker.get("python"),
                "automatic_application_version": old_version,
                "migration_versions": old_worker.get(
                    "system_database_schema_and_migrations", {}
                ).get("migration_records", []),
            },
            "dbos_3_0_0": {
                "dbos_version": new_worker.get("dbos_version"),
                "python": new_worker.get("python"),
                "automatic_application_version": new_version,
                "migration_versions": new_worker.get(
                    "system_database_schema_and_migrations", {}
                ).get("migration_records", []),
            },
            "exact_difference": {
                "automatic_application_version_changed": old_version != new_version,
                "dbos_2_31_1_value": old_version,
                "dbos_3_0_0_value": new_version,
            },
            "helper_only_false_compatible_observation": {
                "baseline_automatic_application_version": helper_old_version,
                "changed_automatic_application_version": helper_new_version,
                "automatic_application_version_unchanged": helper_old_version == helper_new_version,
                "baseline_workflow_result": helper_baseline.get("workflow", {}).get("result"),
                "changed_workflow_result": helper_changed.get("workflow", {}).get("result"),
                "workflow_result_changed": helper_baseline.get("workflow", {}).get("result")
                != helper_changed.get("workflow", {}).get("result"),
                "classification": "false-compatible observation, not compatibility behaviour",
            },
        }
        criteria = comparison.get("criteria")
        if not isinstance(criteria, dict):
            criteria = {}
        version_assertions = {
            "comparison_completed": outcome["returncode"] == 0
            and comparison.get("status") == "passed",
            "exact_dbos_versions_observed": observed["dbos_2_31_1"]["dbos_version"] == "2.31.1"
            and observed["dbos_3_0_0"]["dbos_version"] == "3.0.0",
            "exact_automatic_version_difference_observed": observed["exact_difference"][
                "automatic_application_version_changed"
            ]
            is True,
            "helper_false_compatible_observation": observed[
                "helper_only_false_compatible_observation"
            ]["automatic_application_version_unchanged"]
            is True
            and observed["helper_only_false_compatible_observation"]["workflow_result_changed"]
            is True,
            "python_variant_versions_stable_within_cohort": criteria.get(
                "python_variant_versions_stable_within_cohort"
            )
            is True,
            "exact_isolated_dependency_interpreter_matrix": criteria.get(
                "exact_isolated_dependency_interpreter_matrix"
            )
            is True,
            "cross_dbos_version_difference_observed": criteria.get(
                "cross_dbos_version_difference_observed"
            )
            is True,
        }
        compatibility_revision = "gate03-accepted-revision-2026-09-20"
        result = {
            **common,
            "public_api_only": False,
            "expected": (
                "runtime version comparison observation plus the accepted ADR-0077 "
                "policy fields accepted requirements: released compatibility-revision "
                "and all-prior-cohort drain"
            ),
            "actual": {
                "observed_runtime_version_comparison": observed,
                "assertions": version_assertions,
                "policy_requirements_adr_0077": {
                    "graft_compatibility_revision": compatibility_revision,
                    "graft_compatibility_revision_is_mutable_git_sha_or_image_tag": False,
                    "graft_all_prior_cohort_drain_required": True,
                    "graft_drain_states": ["PENDING", "ENQUEUED", "DELAYED"],
                    "graft_orphan_revision_alert_required": True,
                    "graft_rollback_is_reverse_drain": True,
                    "graft_matching_revision_recovery_only": True,
                },
            },
            "command": outcome,
            "evidence_lanes": {
                "public_api_behaviour": False,
                "private_or_diagnostic": True,
                "private_or_diagnostic_kinds": [
                    "private DBOS runtime, source and schema diagnostic lane; "
                    "not public API behaviour"
                ],
            },
            "verdict": "PASS" if all(version_assertions.values()) else "INCOMPLETE",
            "artefacts": [_evidence_reference("dbos-version-comparison-result.json")],
        }
        _write("04-versioning.json", result)
    else:
        raise ValueError(report)
    report_file = {
        "async-mcp": "01-async-mcp.json",
        "alive-silent": "02-alive-silent.json",
        "listing": "03-listing.json",
        "versioning": "04-versioning.json",
    }[report]
    written = json.loads((REPORTS / report_file).read_text())
    return 0 if written.get("verdict") == "PASS" else 1


def _json_stdout(command: dict[str, object]) -> dict[str, object]:
    stdout = command.get("stdout")
    if not isinstance(stdout, str):
        return {}
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "report", choices=("async-mcp", "alive-silent", "listing", "versioning", "all")
    )
    args = parser.parse_args()
    reports = (
        ("async-mcp", "alive-silent", "listing", "versioning")
        if args.report == "all"
        else (args.report,)
    )
    shared_experiment = None
    if args.report == "all":
        experiment_command = _python_command("deployment/gate-0.3/run_experiment.py", "run")
        experiment_outcome = _command(experiment_command)
        shared_experiment = (_evidence("result.json"), experiment_outcome)
    statuses = [run(report, shared_experiment=shared_experiment) for report in reports]
    return 0 if all(status == 0 for status in statuses) else 1


if __name__ == "__main__":
    raise SystemExit(main())
