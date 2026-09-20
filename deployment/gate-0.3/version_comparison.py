#!/usr/bin/env python3
"""Run the bounded DBOS 2.31.1/3.0.0 application-version comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "specs/phase-1-walking-skeleton/evidence/gate-0.3"
COMPOSE = ROOT / "deployment/gate-0.3/version-comparison-compose.yml"
ENV_FILE = ROOT / "deployment/gate-0.3/.env"
WORKER = ROOT / "deployment/gate-0.3/runtime-version-worker.py"
HELPER_BASELINE = ROOT / "deployment/gate-0.3/version-variants/runtime_helper_baseline.py"
HELPER_CHANGED = ROOT / "deployment/gate-0.3/version-variants/runtime_helper_changed.py"
PASSWORD = "gate03_local_only"
APP_NAME = "gate-0-3-db-version-compare"
REDACTED = "[REDACTED]"

COHORTS: dict[str, dict[str, str]] = {
    "dbos_2_31_1": {
        "dbos": "2.31.1",
        "database": "gate03_dbos_2311_system",
        "schema": "dbos_2311",
        "port": "57441",
    },
    "dbos_3_0_0": {
        "dbos": "3.0.0",
        "database": "gate03_dbos_300_system",
        "schema": "dbos_300",
        "port": "57440",
    },
}
PYTHON_VARIANTS = {
    "3.11": "3.11.11",
    "3.12": "3.12.6",
    "3.13": "3.13.0",
}
ISOLATED_DEPENDENCIES = (
    "click==8.5.0",
    "greenlet==3.5.6",
    "psycopg==3.3.6",
    "psycopg-binary==3.3.6",
    "python-dateutil==2.9.0.post0",
    "PyYAML==6.0.3",
    "six==1.17.0",
    "SQLAlchemy==2.0.54",
    "typing_extensions==4.16.0",
    "websockets==17.1",
)


def _redact(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return value.replace(PASSWORD, REDACTED)
    return value


def _write_json(name: str, value: object) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(json.dumps(_redact(value), indent=2, sort_keys=True) + "\n")


def _command(
    command: list[str], *, env: dict[str, str] | None = None, timeout: int = 300
) -> dict[str, object]:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=timeout,
    )
    return {
        "command": _redact(command),
        "returncode": completed.returncode,
        "stdout": _redact(completed.stdout),
        "stderr": _redact(completed.stderr),
    }


def _runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "G03_DB_USER": "gate03",
            "G03_DB_PASSWORD": PASSWORD,
            "G03_DBOS_2311_SYSTEM_DB": COHORTS["dbos_2_31_1"]["database"],
            "G03_DBOS_300_SYSTEM_DB": COHORTS["dbos_3_0_0"]["database"],
        }
    )
    return env


def _write_env() -> None:
    ENV_FILE.write_text(
        "# Generated for the disposable Gate 0.3 DBOS comparison; ignored by git.\n"
        "G03_DB_USER=gate03\n"
        f"G03_DB_PASSWORD={PASSWORD}\n"
        "G03_APP_DB=gate03_app\n"
        "G03_SYSTEM_DB=gate03_system\n"
        f"G03_DBOS_2311_SYSTEM_DB={COHORTS['dbos_2_31_1']['database']}\n"
        f"G03_DBOS_300_SYSTEM_DB={COHORTS['dbos_3_0_0']['database']}\n"
    )


def _compose(*args: str, timeout: int = 300) -> dict[str, object]:
    return _command(
        [
            "docker",
            "compose",
            "--env-file",
            str(ENV_FILE),
            "-f",
            str(COMPOSE),
            *args,
        ],
        env=_runtime_env(),
        timeout=timeout,
    )


def _database_url(cohort: dict[str, str]) -> str:
    return (
        f"postgresql://gate03@127.0.0.1:{cohort['port']}/{cohort['database']}?password={PASSWORD}"
    )


def _worker_command(
    cohort: dict[str, str], python_label: str, *, helper: Path | None = None
) -> list[str]:
    command = [
        "uv",
        "run",
        "--isolated",
        "--no-project",
        "--python",
        PYTHON_VARIANTS[python_label],
        "--with",
        f"dbos=={cohort['dbos']}",
    ]
    for dependency in ISOLATED_DEPENDENCIES:
        command.extend(["--with", dependency])
    command.extend(
        [
            "python",
            str(WORKER),
            "--system-database-url",
            _database_url(cohort),
            "--schema",
            cohort["schema"],
            "--executor-id",
            f"gate03-{cohort['dbos'].replace('.', '')}-{python_label.replace('.', '')}",
            "--application-name",
            APP_NAME,
        ]
    )
    if helper is not None:
        command.extend(["--helper-source", str(helper)])
    return command


def _json_result(command: dict[str, object]) -> dict[str, object]:
    stdout = command.get("stdout")
    if not isinstance(stdout, str):
        return {"status": "blocked", "error": "worker stdout was not text"}
    for line in reversed(stdout.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "status" in value:
            return value
    return {"status": "blocked", "error": "worker emitted no JSON result"}


def _result_fingerprint(result: dict[str, object]) -> str:
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _resolved_distribution_versions(worker: object) -> dict[str, str]:
    if not isinstance(worker, dict):
        return {}
    distributions = worker.get("resolved_distributions")
    if not isinstance(distributions, list):
        return {}
    result: dict[str, str] = {}
    for distribution in distributions:
        if isinstance(distribution, dict):
            name = distribution.get("name")
            version = distribution.get("version")
            if isinstance(name, str) and isinstance(version, str):
                result[name.lower().replace("-", "_")] = version
    return result


def _expected_distribution_versions(dbos_version: str) -> dict[str, str]:
    expected = {"dbos": dbos_version}
    for requirement in ISOLATED_DEPENDENCIES:
        name, version = requirement.split("==", maxsplit=1)
        expected[name.lower().replace("-", "_")] = version
    return expected


def _system_topology() -> dict[str, object]:
    return {
        "application_name": APP_NAME,
        "cohorts": {
            name: {
                "dbos_version": cohort["dbos"],
                "postgres_database": cohort["database"],
                "postgres_host_port": cohort["port"],
                "dbos_system_schema": cohort["schema"],
                "database_url_password_redacted": (
                    f"postgresql://gate03@127.0.0.1:{cohort['port']}/"
                    f"{cohort['database']}?password={REDACTED}"
                ),
            }
            for name, cohort in COHORTS.items()
        },
        "separation_assertions": {
            "different_postgres_databases": True,
            "different_dbos_system_schemas": True,
            "shared_system_database_or_schema": False,
            "customer_system_access": False,
            "application_database_used": False,
        },
    }


def _run_worker(
    cohort: dict[str, str], python: str, *, helper: Path | None = None
) -> tuple[dict[str, object], dict[str, object]]:
    command = _worker_command(cohort, python, helper=helper)
    command_result = _command(command, env=_runtime_env(), timeout=180)
    result = _json_result(command_result)
    if result.get("status") == "passed":
        result["runner_result_fingerprint"] = _result_fingerprint(result)
    return result, command_result


def run() -> int:
    _write_env()
    started = datetime.now(UTC).isoformat()
    commands: list[dict[str, object]] = []
    compose_up = _compose("up", "-d", "--wait", timeout=180)
    commands.append(compose_up)
    result: dict[str, Any] = {
        "experiment": "gate-0.3-db-version-comparison",
        "started_at": started,
        "runner_python": platform.python_version(),
        "application_name": APP_NAME,
        "system_database_topology": _system_topology(),
        "isolation": {
            "uv_command_mode": "uv run --isolated --no-project",
            "python_interpreter_matrix": PYTHON_VARIANTS,
            "isolated_dependency_versions": list(ISOLATED_DEPENDENCIES),
            "project_lock_read_or_modified": False,
            "comparison_uses_locked_project_environment": False,
            "same_minimal_registered_workflow_source": True,
            "same_application_name": True,
        },
        "compose_up": compose_up,
        "version_matrix": {},
        "helper_runtime_comparison": {},
        "source_probe_boundary": {
            "not_run_by_this_comparison": True,
            "note": (
                "The matrix below is an actual DBOS launch/runtime comparison. "
                "Any source-only hash probe is separate evidence and is not used "
                "as the runtime result."
            ),
        },
    }
    try:
        if compose_up["returncode"] != 0:
            result["status"] = "blocked"
            result["error"] = "comparison PostgreSQL services did not start"
            return 1

        for cohort_name, cohort in COHORTS.items():
            cohort_results: dict[str, object] = {}
            for python_label in PYTHON_VARIANTS:
                worker_result, command_result = _run_worker(cohort, python_label)
                cohort_results[python_label] = {
                    "worker": worker_result,
                    "command": command_result,
                }
                commands.append(command_result)
            result["version_matrix"][cohort_name] = cohort_results

        helper_cohort = COHORTS["dbos_3_0_0"]
        for label, helper_source in (
            ("baseline", HELPER_BASELINE),
            ("changed", HELPER_CHANGED),
        ):
            worker_result, command_result = _run_worker(helper_cohort, "3.13", helper=helper_source)
            result["helper_runtime_comparison"][label] = {
                "worker": worker_result,
                "command": command_result,
                "source_probe": {
                    "performed": False,
                    "note": "This is an actual launch/runtime helper result, not a source probe.",
                },
            }
            commands.append(command_result)

        matrix = result["version_matrix"]
        assert isinstance(matrix, dict)
        passed = [
            matrix[cohort_name][python]["worker"]
            for cohort_name in COHORTS
            for python in PYTHON_VARIANTS
            if isinstance(matrix[cohort_name], dict)
            and isinstance(matrix[cohort_name][python], dict)
            and isinstance(matrix[cohort_name][python].get("worker"), dict)
            and matrix[cohort_name][python]["worker"].get("status") == "passed"
        ]
        by_version = {
            cohort_name: [
                matrix[cohort_name][python]["worker"]
                for python in PYTHON_VARIANTS
                if isinstance(matrix[cohort_name], dict)
                and isinstance(matrix[cohort_name][python], dict)
            ]
            for cohort_name in COHORTS
        }
        versions = {
            cohort_name: sorted(
                {
                    worker.get("launch_runtime_application_version_fields", {})
                    .get("GlobalParams", {})
                    .get("app_version")
                    for worker in workers
                    if isinstance(worker, dict)
                }
                - {None}
            )
            for cohort_name, workers in by_version.items()
        }
        helper_results = result["helper_runtime_comparison"]
        assert isinstance(helper_results, dict)
        baseline_worker = helper_results["baseline"]["worker"]
        changed_worker = helper_results["changed"]["worker"]
        baseline_runtime_fields = (
            baseline_worker.get("launch_runtime_application_version_fields", {})
            if isinstance(baseline_worker, dict)
            else {}
        )
        changed_runtime_fields = (
            changed_worker.get("launch_runtime_application_version_fields", {})
            if isinstance(changed_worker, dict)
            else {}
        )
        baseline_automatic_version = (
            baseline_runtime_fields.get("GlobalParams", {}).get("app_version")
            if isinstance(baseline_runtime_fields, dict)
            else None
        )
        changed_automatic_version = (
            changed_runtime_fields.get("GlobalParams", {}).get("app_version")
            if isinstance(changed_runtime_fields, dict)
            else None
        )
        helper_same_version = (
            isinstance(baseline_worker, dict)
            and isinstance(changed_worker, dict)
            and baseline_automatic_version is not None
            and baseline_automatic_version == changed_automatic_version
        )
        helper_different_results = (
            isinstance(baseline_worker, dict)
            and isinstance(changed_worker, dict)
            and baseline_worker.get("workflow", {}).get("result")
            != changed_worker.get("workflow", {}).get("result")
        )
        exact_matrix = all(
            isinstance(matrix[cohort_name], dict)
            and isinstance(matrix[cohort_name][python], dict)
            and isinstance(matrix[cohort_name][python].get("worker"), dict)
            and matrix[cohort_name][python]["worker"].get("status") == "passed"
            and matrix[cohort_name][python]["worker"].get("python") == PYTHON_VARIANTS[python]
            and _resolved_distribution_versions(matrix[cohort_name][python]["worker"])
            == _expected_distribution_versions(COHORTS[cohort_name]["dbos"])
            for cohort_name in COHORTS
            for python in PYTHON_VARIANTS
        )
        python_stable = all(len(version_set) == 1 for version_set in versions.values())
        cross_dbos_version_diff = bool(
            versions["dbos_2_31_1"]
            and versions["dbos_3_0_0"]
            and versions["dbos_2_31_1"] != versions["dbos_3_0_0"]
        )
        helper_false_compatible = bool(helper_same_version and helper_different_results)
        result["criteria"] = {
            "all_six_real_launches_passed": len(passed) == 6,
            "dbos_2_31_1_runtime_version_recorded": bool(versions["dbos_2_31_1"]),
            "dbos_3_0_0_runtime_version_recorded": bool(versions["dbos_3_0_0"]),
            "runtime_versions_differ_diagnostic_only": cross_dbos_version_diff,
            "cross_dbos_version_difference_observed": cross_dbos_version_diff,
            "python_variant_versions_stable_within_cohort": python_stable,
            "exact_isolated_dependency_interpreter_matrix": exact_matrix,
            "helper_runtime_launches_passed": all(
                isinstance(helper_results[label]["worker"], dict)
                and helper_results[label]["worker"].get("status") == "passed"
                for label in ("baseline", "changed")
            ),
            "helper_only_runtime_same_application_version": bool(helper_same_version),
            "helper_only_runtime_result_changed": bool(helper_different_results),
            "helper_only_runtime_is_false_compatible": helper_false_compatible,
            "helper_false_compatible_observation": helper_false_compatible,
        }
        required_criteria = (
            "all_six_real_launches_passed",
            "python_variant_versions_stable_within_cohort",
            "exact_isolated_dependency_interpreter_matrix",
            "cross_dbos_version_difference_observed",
            "helper_false_compatible_observation",
        )
        if all(result["criteria"][name] for name in required_criteria):
            result["status"] = "passed"
            result["direct_conclusion"] = (
                "Observed in private runtime diagnostics only: with the same registered minimal "
                "workflow source and application name, DBOS 2.31.1 and DBOS 3.0.0 computed "
                "different automatic application-version values. This is not the compatibility "
                "boundary and does not select a drain subset."
            )
        else:
            result["status"] = "blocked"
            result["direct_conclusion"] = (
                "No conclusion: one or more DBOS version launches failed or did not expose "
                "distinct runtime application-version fields."
            )
        result["adr_0077_disposition"] = (
            "OBSERVED_DIAGNOSTICS_WITH_ACCEPTED_ADR_0077_POLICY: explicit released "
            "compatibility revisions and all-prior-cohort drain are the boundary"
            if result["status"] == "passed"
            else "blocked; ADR-0077 mitigation evidence is incomplete"
        )
    finally:
        compose_down = _compose("down", "-v", timeout=180)
        commands.append(compose_down)
        result["commands"] = commands
        result["finished_at"] = datetime.now(UTC).isoformat()
        _write_json("dbos-version-comparison-result.json", result)
        _write_json("dbos-version-comparison-commands.json", commands)
    return 0 if result.get("status") == "passed" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run",))
    args = parser.parse_args()
    del args
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
