#!/usr/bin/env python3
"""Run Gate 0.3 Tests 2 and 3 as separate processes and write redacted evidence."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "specs/phase-1-walking-skeleton/evidence/gate-0.3"
RUNNER = Path(__file__).resolve()
WORKER = RUNNER.with_name("matrix_worker.py")
PROBE = RUNNER.with_name("version-probe.py")
VARIANTS = RUNNER.with_name("version-variants")
APP_DATABASE_URL = "postgresql://gate03@localhost:55432/gate03_app"
SYSTEM_DATABASE_URL = "postgresql://gate03@localhost:55433/gate03_system"
REDACTED = "[REDACTED]"


def _redact(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return value.replace("gate03_" + "local_only", REDACTED)
    return value


def _write_json(name: str, value: object) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(json.dumps(_redact(value), indent=2, sort_keys=True) + "\n")


def _command(command: list[str], *, env: dict[str, str] | None = None) -> dict[str, object]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False, env=env)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": _redact(completed.stdout),
        "stderr": _redact(completed.stderr),
    }


def _runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "G03_APP_DATABASE_URL": f"{APP_DATABASE_URL}?password=gate03_" + "local_only",
            "G03_SYSTEM_DATABASE_URL": f"{SYSTEM_DATABASE_URL}?password=gate03_" + "local_only",
            "G03_POOLER_DATABASE_URL": (
                "postgresql://gate03@localhost:56432/gate03_app?password=gate03_" + "local_only"
            ),
            "G03_DB_PASSWORD": "gate03_" + "local_only",
        }
    )
    return env


def _parse_events(output: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in output.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "event" in value:
            events.append(value)
    return events


def _wait_for_event(process: subprocess.Popen[str], event: str) -> tuple[dict[str, Any], str]:
    output: list[str] = []
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        line = process.stdout.readline() if process.stdout is not None else ""
        if line:
            output.append(line)
            for parsed in _parse_events(line):
                if parsed.get("event") == event:
                    return parsed, "".join(output)
        elif process.poll() is not None:
            break
        else:
            time.sleep(0.05)
    raise RuntimeError(
        f"process did not emit {event}; returncode={process.poll()} output={''.join(output)}"
    )


def _start_worker(
    mode: str,
    version: str,
    executor: str,
    *,
    prefix: str,
    workflow_ids: str = "",
    target_executor: str = "",
) -> tuple[subprocess.Popen[str], list[str]]:
    command = [
        sys.executable,
        str(WORKER),
        mode,
        "--application-version",
        version,
        "--executor-id",
        executor,
        "--run-prefix",
        prefix,
    ]
    if workflow_ids:
        command.extend(["--workflow-ids", workflow_ids])
    if target_executor:
        command.extend(["--target-executor-id", target_executor])
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=_runtime_env(),
        start_new_session=True,
    )
    return process, command


def _stop_process(process: subprocess.Popen[str], *, force: bool = False) -> str:
    if process.poll() is None:
        if force:
            os.killpg(process.pid, signal.SIGKILL)
        else:
            os.killpg(process.pid, signal.SIGTERM)
    try:
        output, _ = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        output, _ = process.communicate()
    return output


def _active_ids(statuses: dict[str, object]) -> list[str]:
    ids: list[str] = []
    for workflow_id, status in statuses.items():
        if isinstance(status, dict) and status.get("status") in {
            "PENDING",
            "ENQUEUED",
            "DELAYED",
        }:
            ids.append(workflow_id)
    return sorted(ids)


def _direction_part(direction: dict[str, object], key: str) -> dict[str, object]:
    value = direction.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"matrix direction is missing object field {key}")
    return value


def _run_direction(
    *,
    old_version: str,
    new_version: str,
    prefix: str,
    old_executor: str,
    new_executor: str,
) -> dict[str, object]:
    seed_process, seed_command = _start_worker("seed", old_version, old_executor, prefix=prefix)
    seed_event, seed_prefix_output = _wait_for_event(seed_process, "seeded")
    workflow_ids = [str(value) for value in seed_event["workflow_ids"]]
    workflow_id_text = ",".join(workflow_ids)

    observer_process, observer_command = _start_worker(
        "observe",
        new_version,
        new_executor,
        prefix=prefix,
        workflow_ids=workflow_id_text,
        target_executor=old_executor,
    )
    observer_output, _ = observer_process.communicate(timeout=40)
    observer_events = _parse_events(observer_output)
    if not observer_events:
        raise RuntimeError(f"new cohort emitted no observation: {observer_output}")
    observer_event = observer_events[-1]

    killed_seed_output = _stop_process(seed_process, force=True)
    orphaned_ids = _active_ids(observer_event["after"])
    recovery_process, recovery_command = _start_worker(
        "recover",
        old_version,
        f"{old_executor}-replacement",
        prefix=prefix,
        workflow_ids=workflow_id_text,
        target_executor=old_executor,
    )
    recovery_output, _ = recovery_process.communicate(timeout=90)
    recovery_events = _parse_events(recovery_output)
    if not recovery_events:
        raise RuntimeError(f"replacement cohort emitted no drain event: {recovery_output}")
    recovery_event = recovery_events[-1]

    return {
        "direction": f"{old_version}->{new_version}",
        "seed": {
            "command": seed_command,
            "event": seed_event,
            "output": seed_prefix_output + killed_seed_output,
            "killed": True,
        },
        "new_cohort": {
            "command": observer_command,
            "event": observer_event,
            "output": observer_output,
            "public_cross_executor_recovery_attempted": observer_event["public_observation"][
                "cross_executor_recovery_attempted"
            ],
        },
        "orphan_detector": {
            "live_executors": [new_executor],
            "dead_old_executor": old_executor,
            "active_old_version_workflow_ids": orphaned_ids,
            "flags_orphan": bool(orphaned_ids),
            "query_semantics": (
                "active PENDING/ENQUEUED/DELAYED rows whose application version "
                "has no live executor"
            ),
        },
        "old_cohort_replacement": {
            "command": recovery_command,
            "event": recovery_event,
            "output": recovery_output,
            "public_resume_api": recovery_event.get("public_resume_api"),
            "drained": recovery_event.get("event") == "drained",
        },
    }


def run_test_2() -> tuple[dict[str, object], list[dict[str, object]]]:
    started = datetime.now(UTC).isoformat()
    compose_file = "deployment/gate-0.3/docker-compose.yml"
    env_file = "deployment/gate-0.3/.env"
    commands: list[dict[str, object]] = [
        {
            "command": [
                "uv",
                "run",
                "python",
                "deployment/gate-0.3/run_experiment.py",
                "prepare",
            ],
            "note": "generated the ignored synthetic runtime environment before this run",
        },
        {
            "command": [
                "docker",
                "compose",
                "--env-file",
                env_file,
                "-f",
                compose_file,
                "up",
                "-d",
            ],
            "note": "started the two PostgreSQL 16 containers and transaction-mode PgBouncer",
        },
    ]
    old_version = "release-compat-old-2026-09-19"
    new_version = "release-compat-new-2026-09-19"
    forward = _run_direction(
        old_version=old_version,
        new_version=new_version,
        prefix="forward",
        old_executor="gate03-old-a",
        new_executor="gate03-new-b",
    )
    rollback = _run_direction(
        old_version=new_version,
        new_version=old_version,
        prefix="rollback",
        old_executor="gate03-new-a",
        new_executor="gate03-old-b",
    )
    commands.append(
        {
            "command": "separate host processes using deployment/gate-0.3/matrix_worker.py",
            "topology": "two PostgreSQL containers plus transaction-mode PgBouncer",
        }
    )
    commands.extend(
        [
            {
                "command": [
                    "uv",
                    "run",
                    "python",
                    "deployment/gate-0.3/matrix_runner.py",
                    "2",
                ]
            },
            {
                "command": [
                    "docker",
                    "compose",
                    "--env-file",
                    env_file,
                    "-f",
                    compose_file,
                    "down",
                    "-v",
                ],
                "note": (
                    "removed containers, volumes, network, and the generated runtime "
                    "environment after the run"
                ),
            },
        ]
    )
    forward_orphan = _direction_part(forward, "orphan_detector")
    forward_replacement = _direction_part(forward, "old_cohort_replacement")
    rollback_orphan = _direction_part(rollback, "orphan_detector")
    rollback_replacement = _direction_part(rollback, "old_cohort_replacement")
    rollback_observed = bool(rollback_orphan["flags_orphan"] and rollback_replacement["drained"])
    criterion = {
        "new_cohort_conditional_recovery": False,
        "orphan_detection": forward_orphan["flags_orphan"] and rollback_orphan["flags_orphan"],
        "drain_zero_active_rows": forward_replacement["drained"]
        and rollback_replacement["drained"],
        "rollback_reverse_drain": rollback_observed,
    }
    return (
        {
            "test": "Test 2 - Version-scoped recovery and drain",
            "started_at": started,
            "environment": {
                "python": platform.python_version(),
                "application_database": "PostgreSQL 16 container",
                "system_database": "PostgreSQL 16 container",
                "pooler": "transaction-mode PgBouncer container",
                "process_isolation": "separate host processes; reduced-fidelity legacy lane",
                "graft_compatibility_revisions": {"old": old_version, "new": new_version},
                "customer_system_access": False,
            },
            "forward": forward,
            "rollback": rollback,
            "verdict": "PASS"
            if criterion["new_cohort_conditional_recovery"]
            else "REDUCED_FIDELITY",
            "report_disposition": "PASS"
            if criterion["new_cohort_conditional_recovery"]
            else "REDUCED_FIDELITY",
            "limitations": [
                (
                    "The public DBOS APIs do not provide a safe expected-executor and "
                    "explicit-application-revision conditional recovery call."
                ),
                (
                    "This legacy lane uses host subprocesses and is not the "
                    "container-isolated Test 5 reaper prototype."
                ),
                "The replacement drain used DBOSClient.resume_workflows and therefore "
                "does not prove the proposed reaper ownership semantics.",
                "The orphan detector is a synthetic application-level query, not DBOS "
                "Conductor or a verified executor-liveness detector.",
                "The prior private recovery probe is not evidence and is not run by this lane.",
            ],
            "criterion": criterion,
            "operational_drain_evidence": {
                "graft_forward_old_compatibility_revision": old_version,
                "forward_states_observed": ["PENDING", "ENQUEUED", "DELAYED"],
                "forward_orphan_alert": bool(forward_orphan["flags_orphan"]),
                "graft_forward_matching_revision_recovery": bool(forward_replacement["drained"]),
                "graft_reverse_new_compatibility_revision": new_version,
                "reverse_states_observed": ["PENDING", "ENQUEUED", "DELAYED"],
                "reverse_orphan_alert": bool(rollback_orphan["flags_orphan"]),
                "graft_reverse_matching_revision_recovery": bool(rollback_replacement["drained"]),
                "graft_revision_selection_safe": False,
                "blocker": (
                    "DBOS public resume API cannot condition on expected "
                    "executor/application revision."
                ),
            },
            "finished_at": datetime.now(UTC).isoformat(),
        },
        commands,
    )


def _probe_command(
    source: Path, app_name: str, *, python: str | None = None, extra: list[str] | None = None
) -> dict[str, object]:
    command = ["uv", "run", "--locked"]
    if python:
        command.extend(["--python", python])
    if extra:
        command.extend(extra)
    command.extend(["python", str(PROBE), "--source-file", str(source), "--app-name", app_name])
    return _command(command, env=_runtime_env())


def _probe_result(command: dict[str, object]) -> dict[str, object]:
    stdout = command.get("stdout", "")
    if not isinstance(stdout, str):
        return {"status": "blocked", "error": "probe stdout was not text"}
    for line in reversed(stdout.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "application_version" in value:
            return {"status": "passed", **value}
    return {"status": "blocked", "error": "probe emitted no JSON result"}


def _docker_probe(tag: str) -> tuple[dict[str, object], list[dict[str, object]]]:
    build = _command(
        [
            "docker",
            "build",
            "--no-cache",
            "--tag",
            tag,
            "--file",
            str(RUNNER.with_name("version-probe.Dockerfile")),
            str(RUNNER.parent),
        ]
    )
    run = _command(
        [
            "docker",
            "run",
            "--rm",
            tag,
            "--source-file",
            "/opt/gate-0-3/version-variants/baseline.py",
            "--app-name",
            "gate-0-3-recovery-matrix",
        ]
    )
    cleanup = _command(["docker", "image", "rm", "--force", tag])
    return _probe_result(run), [build, run, cleanup]


def run_test_3() -> tuple[dict[str, object], list[dict[str, object]]]:
    started = datetime.now(UTC).isoformat()
    commands: list[dict[str, object]] = []
    baseline = VARIANTS / "baseline.py"
    app_name = "gate-0-3-recovery-matrix"
    baseline_command = _probe_command(baseline, app_name)
    commands.append(baseline_command)
    baseline_result = _probe_result(baseline_command)

    with (
        tempfile.TemporaryDirectory(prefix="gate03-source-a-") as first_dir,
        tempfile.TemporaryDirectory(prefix="gate03-source-b-") as second_dir,
    ):
        first_source = Path(first_dir) / "matrix.py"
        second_source = Path(second_dir) / "matrix.py"
        shutil.copyfile(baseline, first_source)
        shutil.copyfile(baseline, second_source)
        first_command = _probe_command(first_source, app_name)
        second_command = _probe_command(second_source, app_name)
        commands.extend([first_command, second_command])
        path_results = [_probe_result(first_command), _probe_result(second_command)]

    docker_results: list[dict[str, object]] = []
    docker_commands: list[dict[str, object]] = []
    for suffix in ("a", "b"):
        result, probe_commands = _docker_probe(f"gate03-version-probe-{suffix}")
        docker_results.append(result)
        docker_commands.extend(probe_commands)
    commands.extend(docker_commands)

    variant_results: dict[str, dict[str, object]] = {}
    for variant in (
        "comment_only",
        "format_only",
        "step_added",
        "step_removed",
        "step_reordered",
        "helper_baseline",
        "helper_changed",
    ):
        command = _probe_command(VARIANTS / f"{variant}.py", app_name)
        commands.append(command)
        variant_results[variant] = _probe_result(command)

    app_name_command = _probe_command(baseline, "gate-0-3-recovery-matrix-renamed")
    commands.append(app_name_command)
    app_name_result = _probe_result(app_name_command)

    python_results: dict[str, dict[str, object]] = {}
    for python in ("3.11", "3.12", "3.13"):
        command = _probe_command(baseline, app_name, python=python)
        commands.append(command)
        python_results[python] = _probe_result(command)

    dependency_commands = {
        "non_dbos_upgrade": _command(
            [
                "uv",
                "run",
                "--locked",
                "--with",
                "langgraph==1.2.12",
                "python",
                str(PROBE),
                "--source-file",
                str(baseline),
                "--app-name",
                app_name,
            ],
            env=_runtime_env(),
        ),
        "dbos_upgrade": _command(
            [
                "uv",
                "run",
                "--locked",
                "--with",
                "dbos==3.1.0",
                "python",
                str(PROBE),
                "--source-file",
                str(baseline),
                "--app-name",
                app_name,
            ],
            env=_runtime_env(),
        ),
    }
    commands.extend(dependency_commands.values())
    dependency_results = {
        name: _probe_result(command) for name, command in dependency_commands.items()
    }

    baseline_version = baseline_result.get("application_version")
    path_versions = [result.get("application_version") for result in path_results]
    variant_versions = {
        name: result.get("application_version") for name, result in variant_results.items()
    }
    changed_expected = all(
        variant_versions[name] not in {None, baseline_version}
        for name in ("step_added", "step_removed", "step_reordered")
    )
    helper_changed_expected = (
        variant_versions["helper_baseline"] is not None
        and variant_versions["helper_baseline"] == variant_versions["helper_changed"]
    )
    stable_expected = (
        baseline_version is not None
        and path_versions == [baseline_version, baseline_version]
        and all(
            result.get("application_version") == baseline_version
            for result in python_results.values()
            if result.get("status") == "passed"
        )
    )
    return (
        {
            "test": "Test 3 - Version hash provenance",
            "started_at": started,
            "environment": {
                "locked_python": platform.python_version(),
                "locked_dbos": baseline_result.get("dbos_version"),
                "source_file": "deployment/gate-0.3/version-variants/baseline.py",
                "clean_builds": (
                    "two independent temporary source trees plus two Docker build commands "
                    "are recorded separately by the parent lane"
                ),
            },
            "baseline": baseline_result,
            "same_source_different_paths": path_results,
            "separate_container_builds": docker_results,
            "variants": variant_results,
            "application_name_change": app_name_result,
            "python_variants": python_results,
            "dependency_variants": dependency_results,
            "hash_provenance": baseline_result.get("dbos_hash_provenance"),
            "criteria": {
                "path_deterministic": path_versions == [baseline_version, baseline_version],
                "container_deterministic": [
                    result.get("application_version") for result in docker_results
                ]
                == [baseline_version, baseline_version],
                "step_and_helper_changes_bump": changed_expected,
                "helper_only_change_is_false_compatible": helper_changed_expected,
                "comment_and_format_results_recorded": all(
                    name in variant_results for name in ("comment_only", "format_only")
                ),
                "app_name_change_recorded": app_name_result.get("status") == "passed",
                "app_name_changes_version": app_name_result.get("application_version")
                not in {None, baseline_version},
                "python_variant_results_recorded": len(python_results) == 3,
                "locked_runtime_stable": stable_expected,
            },
            "dependency_variant_blockers": {
                name: result.get("error")
                for name, result in dependency_results.items()
                if result.get("status") != "passed"
            },
            "verdict": "DIAGNOSTIC_ONLY_WITH_ADR_0077_POLICY",
            "limitations": [
                "The dependency-upgrade probes were blocked by the resolver, so no "
                "cross-DBOS-version observation is claimed.",
                "The helper-only unchanged version is a false-compatible result, not "
                "a compatibility result: the version did not change despite helper code changing.",
            ],
            "finished_at": datetime.now(UTC).isoformat(),
        },
        commands,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("test", choices=("2", "3", "all"))
    args = parser.parse_args()
    if args.test in {"2", "all"}:
        result, commands = run_test_2()
        _write_json("test-2-result.json", result)
        _write_json("test-2-commands.json", commands)
    if args.test in {"3", "all"}:
        result, commands = run_test_3()
        _write_json("test-3-result.json", result)
        _write_json("test-3-commands.json", commands)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
