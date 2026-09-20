"""Run the bounded Temporal comparison against the local disposable server."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar
from uuid import uuid4

from temporal_spike import (
    TASK_QUEUE,
    TEMPORAL_ADDRESS,
    CompatibilityWorkflow,
    RecoveryWorkflow,
)
from temporalio.client import Client, WorkflowHistory
from temporalio.worker import Replayer

ROOT = Path(__file__).resolve().parents[2]
WORKER_SCRIPT = Path(__file__).with_name("temporal_spike.py")


class SyntheticReceiver(BaseHTTPRequestHandler):
    """Keyed receiver that records raw deliveries and applies one logical effect."""

    raw_calls: ClassVar[list[dict[str, str]]] = []
    keyed_effects: ClassVar[set[str]] = set()
    lock = threading.Lock()

    def do_POST(self) -> None:
        length = int(self.headers["Content-Length"] or "0")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        effect_key = str(payload["effect_key"])
        with self.lock:
            self.raw_calls.append(payload)
            applied = effect_key not in self.keyed_effects
            self.keyed_effects.add(effect_key)
            result = {
                "raw_call_number": str(len(self.raw_calls)),
                "effect_key": effect_key,
                "applied": str(applied).lower(),
            }
        encoded = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return

    @classmethod
    def snapshot(cls) -> dict[str, Any]:
        with cls.lock:
            return {
                "raw_call_count": len(cls.raw_calls),
                "keyed_logical_effect_count": len(cls.keyed_effects),
                "raw_calls": list(cls.raw_calls),
            }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _redact_history(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact_history(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_history(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"@[A-Za-z0-9_.-]+", "@[redacted-host]", value)
    return value


def _history_json(history: WorkflowHistory) -> dict[str, Any]:
    return _redact_history(history.to_json_dict())


def _history_observations(history: dict[str, Any]) -> dict[str, Any]:
    events = history.get("events", [])
    event_types = [event.get("eventType", "") for event in events]
    timeout_types: list[str] = []
    activity_failure_timeout_types: list[str] = []
    marker_names: list[str] = []
    for event in events:
        attributes = event.get("activityTaskTimedOutEventAttributes", {})
        if attributes.get("timeoutType"):
            timeout_types.append(attributes["timeoutType"])
        activity_started = event.get("activityTaskStartedEventAttributes", {})
        timeout_failure = activity_started.get("lastFailure", {}).get("timeoutFailureInfo", {})
        if timeout_failure.get("timeoutType"):
            activity_failure_timeout_types.append(timeout_failure["timeoutType"])
        marker = event.get("markerRecordedEventAttributes", {})
        if marker.get("markerName"):
            marker_names.append(marker["markerName"])
    return {
        "event_types": event_types,
        "activity_timeout_types": timeout_types,
        "activity_retry_failure_timeout_types": activity_failure_timeout_types,
        "marker_names": marker_names,
        "activity_heartbeat_timeout_observed": "TIMEOUT_TYPE_HEARTBEAT"
        in activity_failure_timeout_types,
        "activity_task_timed_out_observed": bool(timeout_types)
        or bool(activity_failure_timeout_types),
    }


def _launch_worker(evidence_dir: Path, name: str, crash_first: bool) -> subprocess.Popen[str]:
    log_path = evidence_dir / f"worker-{name}.log.txt"
    log_file = log_path.open("w")
    environment = os.environ.copy()
    environment.update(
        {
            "TEMPORAL_ADDRESS": TEMPORAL_ADDRESS,
            "SPIKE_CRASH_FIRST": "1" if crash_first else "0",
            "SPIKE_WORKER_ID": f"graft-temporal-{name}",
        }
    )
    process = subprocess.Popen(
        [sys.executable, str(WORKER_SCRIPT), "worker"],
        cwd=ROOT,
        env=environment,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    log_file.close()
    return process


async def _stop_worker(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.terminate()
    try:
        await asyncio.wait_for(asyncio.to_thread(process.wait), timeout=5)
    except TimeoutError:
        process.kill()
        await asyncio.to_thread(process.wait)


async def _wait_for_worker_ready(evidence_dir: Path, name: str) -> None:
    path = evidence_dir / f"worker-{name}.log.txt"
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if path.exists() and '"worker": "ready"' in path.read_text():
            return
        await asyncio.sleep(0.1)
    raise TimeoutError(f"worker {name} did not become ready")


async def _run_recovery_scenario(
    client: Client, evidence_dir: Path, scenario: str, receiver: bool = False
) -> dict[str, Any]:
    receiver_server: ThreadingHTTPServer | None = None
    if receiver:
        SyntheticReceiver.raw_calls = []
        SyntheticReceiver.keyed_effects = set()
        receiver_server = ThreadingHTTPServer(("127.0.0.1", 0), SyntheticReceiver)
        receiver_thread = threading.Thread(target=receiver_server.serve_forever, daemon=True)
        receiver_thread.start()
        os.environ["SPIKE_EFFECT_URL"] = (
            f"http://127.0.0.1:{receiver_server.server_address[1]}/effect"
        )

    workflow_id = f"graft-temporal-spike-{scenario}-{uuid4().hex[:8]}"
    first = _launch_worker(evidence_dir, f"{scenario}-first", crash_first=True)
    await _wait_for_worker_ready(evidence_dir, f"{scenario}-first")
    handle = await client.start_workflow(
        RecoveryWorkflow.run,
        scenario,
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    await asyncio.wait_for(asyncio.to_thread(first.wait), timeout=15)
    replacement = _launch_worker(evidence_dir, f"{scenario}-replacement", crash_first=False)
    await _wait_for_worker_ready(evidence_dir, f"{scenario}-replacement")
    result = await asyncio.wait_for(handle.result(), timeout=30)
    history = await handle.fetch_history()
    history_dict = _history_json(history)
    _write_json(evidence_dir / f"history-{scenario}.json", history_dict)
    receiver_snapshot = None
    if receiver_server is not None:
        receiver_snapshot = SyntheticReceiver.snapshot()
        _write_json(evidence_dir / "synthetic-receiver.json", receiver_snapshot)
        receiver_server.shutdown()
    await _stop_worker(replacement)
    return {
        "workflow_id": workflow_id,
        "result": result,
        "history_observations": _history_observations(history_dict),
        "receiver": receiver_snapshot,
        "first_worker_returncode": first.returncode,
        "replacement_worker_returncode": replacement.returncode,
    }


async def _run_compatibility_scenario(client: Client, evidence_dir: Path) -> dict[str, Any]:
    worker = _launch_worker(evidence_dir, "compatibility", crash_first=False)
    await _wait_for_worker_ready(evidence_dir, "compatibility")
    workflow_id = f"graft-temporal-spike-compatibility-{uuid4().hex[:8]}"
    handle = await client.start_workflow(
        CompatibilityWorkflow.run,
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    result = await asyncio.wait_for(handle.result(), timeout=15)
    history = await handle.fetch_history()
    history_dict = _history_json(history)
    _write_json(evidence_dir / "history-compatibility.json", history_dict)
    replay_result = await Replayer(workflows=[CompatibilityWorkflow]).replay_workflow(history)
    await _stop_worker(worker)
    observations = _history_observations(history_dict)
    return {
        "workflow_id": workflow_id,
        "result": result,
        "history_observations": observations,
        "replay_succeeded": replay_result.replay_failure is None,
        "replay_failure": str(replay_result.replay_failure)
        if replay_result.replay_failure is not None
        else None,
        "capability": "workflow.patched plus SDK Replayer",
        "classification": "PASS" if observations["marker_names"] else "UNSUPPORTED",
    }


async def run(evidence_dir: Path) -> dict[str, Any]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    client: Client | None = None
    last_error: Exception | None = None
    for _ in range(30):
        try:
            client = await Client.connect(TEMPORAL_ADDRESS, namespace="default")
            break
        except Exception as error:
            last_error = error
            await asyncio.sleep(1)
    if client is None:
        raise RuntimeError("Temporal server did not accept a client connection") from last_error
    recovery = await _run_recovery_scenario(client, evidence_dir, "heartbeat_death")
    effect = await _run_recovery_scenario(client, evidence_dir, "keyed_effect", receiver=True)
    compatibility = await _run_compatibility_scenario(client, evidence_dir)
    result = {
        "spike": "bounded-disposable-temporal-comparison",
        "classification": "PASS_WITH_LIMITATIONS",
        "temporal_server": (
            "temporalio/auto-setup:1.29.1@sha256:"
            "5b3502a3b685f9eff1b925af90c57c9e3dbeccbef367cc28a2a9712c63379312"
        ),
        "postgres": (
            "postgres:16.8-alpine@sha256:"
            "3b057e1c2c6dfee60a30950096f3fab33be141dbb0fdd7af3d477083de94166c"
        ),
        "python_sdk": "temporalio==1.20.0",
        "temporal_address": "127.0.0.1:17233",
        "synthetic_only": True,
        "customer_access": False,
        "production_deployment": False,
        "external_effect_fencing": False,
        "scenarios": {
            "hard_worker_death_retry_timeout_heartbeat": recovery,
            "post_effect_death_raw_duplicate_keyed_logical_effect": effect,
            "workflow_compatibility_patch_and_replay": compatibility,
        },
        "capability_classifications": {
            "workflow_patched": "SUPPORTED_AND_OBSERVED",
            "sdk_replayer": "SUPPORTED_AND_OBSERVED",
            "deployment_version_routing": "NOT_TESTED",
            "worker_runtime_heartbeat": "SERVER_REPORTED_UNSUPPORTED; activity heartbeat supported",
        },
        "dbos_specific_capabilities_not_covered": [
            "DBOS step trajectory and list_workflow_steps",
            "DBOS workflow fork_workflow evaluation replay semantics",
            "DBOS partition-key queue flow control and ceiling enforcement",
            "DBOS PostgreSQL system-database and transaction-mode pooler topology",
            "DBOS executor ownership, application compatibility revision and reaper policy",
        ],
        "limitations": [
            "Temporal server does not fence an external effect when a worker is dead "
            "or merely silent.",
            "The receiver-side key made one logical effect from two raw deliveries; "
            "this is not exactly-once execution.",
            "This is a local single-server observation, not production availability, "
            "scaling, or security evidence.",
        ],
    }
    _write_json(evidence_dir / "result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    _write_json(
        args.evidence_dir / "commands.json",
        {
            "command": [
                "uv run --group temporal-spike python "
                "deployment/temporal-spike/run_spike.py "
                "--evidence-dir specs/phase-1-walking-skeleton/evidence/temporal-spike"
            ],
            "server_endpoint": "127.0.0.1:17233",
            "synthetic_credentials": "compose-only placeholders; not recorded",
            "docker_commands": [
                "docker compose -f deployment/temporal-spike/docker-compose.yml up -d --wait",
                "docker compose -f deployment/temporal-spike/docker-compose.yml logs --no-color",
                "docker compose -f deployment/temporal-spike/docker-compose.yml down "
                "-v --remove-orphans",
            ],
        },
    )
    asyncio.run(run(args.evidence_dir))


if __name__ == "__main__":
    main()
