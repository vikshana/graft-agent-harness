#!/usr/bin/env python3
"""Run the supported-API Gate 0.3 post-effect zombie probe.

This is deliberately a narrow probe, not a synthetic recovery simulator.  A
real DBOS workflow calls a keyed HTTP stub from a real DBOS step.  The first
executor is stopped after the stub has recorded the effect but before the HTTP
request (and therefore the step) returns.  A same-version executor is then
started, a wrong-version executor is observed, and the workflow is resumed
using only ``DBOSClient.list_workflows`` and ``DBOSClient.resume_workflow``.

The probe never reads or writes DBOS system tables and never calls DBOS private
recovery functions.  If the public APIs cannot drive the scenario, the output
is recorded as reduced fidelity and no recovery conclusion is made.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import select
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dbos import DBOS, DBOSClient, DBOSConfig, SetWorkflowID

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "specs/phase-1-walking-skeleton/evidence/gate-0.3"
SCRIPT = Path(__file__).resolve()
EFFECT_URL = "http://127.0.0.1:59998/effect"
APP_NAME = "gate-0-3-zombie-race"
WORKFLOW_ID = "g03-real-post-effect-pre-checkpoint"
APP_VERSION = "gate03-race-v1"
WRONG_VERSION = "gate03-race-wrong-v1"
APP_DATABASE_URL = "postgresql://gate03@localhost:55432/gate03_app"
SYSTEM_DATABASE_URL = "postgresql://gate03@localhost:55433/gate03_system"
REDACTED = "[REDACTED]"


def _redact(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return value.replace("gate03_local_only", REDACTED)
    return value


def _write(name: str, value: object) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(json.dumps(_redact(value), indent=2, sort_keys=True) + "\n")


class EffectState:
    def __init__(self) -> None:
        self.condition = threading.Condition()
        self.first_effect = threading.Event()
        self.release_first = threading.Event()
        self.raw_calls = 0
        self.keyed_effects = 0
        self.keys: set[str] = set()
        self.calls: list[dict[str, object]] = []


EFFECT_STATE = EffectState()


class EffectHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        effect_key = str(body["effect_key"])
        with EFFECT_STATE.condition:
            EFFECT_STATE.raw_calls += 1
            first_for_key = effect_key not in EFFECT_STATE.keys
            if first_for_key:
                EFFECT_STATE.keys.add(effect_key)
                EFFECT_STATE.keyed_effects += 1
                EFFECT_STATE.first_effect.set()
            EFFECT_STATE.calls.append(
                {
                    "effect_key": effect_key,
                    "executor_id": body.get("executor_id"),
                    "first_for_key": first_for_key,
                    "raw_call_number": EFFECT_STATE.raw_calls,
                }
            )

        # Keep A's first request open.  A SIGSTOP sent after first_effect is
        # observed therefore lands after the external effect but before the
        # step returns and checkpoints.  A duplicate request is not held.
        if first_for_key:
            EFFECT_STATE.release_first.wait(timeout=30)

        payload = json.dumps({"keyed": first_for_key, "effect_key": effect_key}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *_args: object) -> None:
        return


def _effect_server() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 59998), EffectHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@DBOS.step()
async def keyed_http_step(workflow_id: str, effect_key: str, executor_id: str) -> str:
    payload = json.dumps(
        {"workflow_id": workflow_id, "effect_key": effect_key, "executor_id": executor_id}
    ).encode()
    request = urllib.request.Request(
        EFFECT_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode()


@DBOS.workflow()
async def zombie_workflow(workflow_id: str, effect_key: str, executor_id: str) -> str:
    return await keyed_http_step(workflow_id, effect_key, executor_id)


def _worker_config(args: argparse.Namespace) -> DBOSConfig:
    return {
        "name": APP_NAME,
        "application_version": args.application_version,
        "system_database_url": os.environ["G03_SYSTEM_DATABASE_URL"],
        "executor_id": args.executor_id,
        "run_migrations": args.migrate,
        "use_listen_notify": True,
        "notification_listener_polling_interval_sec": 0.05,
        "notification_coalesce_sec": 0.01,
        "scheduler_polling_interval_sec": 0.05,
        "max_executor_threads": 4,
    }


def _event(event: str, **fields: object) -> None:
    print(json.dumps({"event": event, **fields}, sort_keys=True), flush=True)


async def _worker(args: argparse.Namespace) -> None:
    DBOS.destroy()
    DBOS(config=_worker_config(args))
    DBOS.launch()
    _event(
        "ready",
        application_name=APP_NAME,
        application_version=args.application_version,
        executor_id=args.executor_id,
        migrations=args.migrate,
    )
    try:
        if args.role == "a":
            with SetWorkflowID(WORKFLOW_ID):
                handle = await DBOS.start_workflow_async(
                    zombie_workflow,
                    WORKFLOW_ID,
                    f"{WORKFLOW_ID}:effect-step",
                    args.executor_id,
                )
            _event("started", workflow_id=handle.get_workflow_id())
            try:
                result = await handle.get_result(polling_interval_sec=0.05)
            except Exception as exc:
                _event("workflow_error", error_type=type(exc).__name__, error=str(exc))
            else:
                _event("workflow_result", result=result)
        else:
            # The parent drives the public resume call.  Keeping this worker
            # alive lets DBOS's normal queue executor process that request.
            await asyncio.Event().wait()
    finally:
        if args.role == "a":
            DBOS.destroy()


def _status_dict(status: object) -> dict[str, object]:
    return {
        field: getattr(status, field, None)
        for field in (
            "workflow_id",
            "workflow_uuid",
            "status",
            "name",
            "executor_id",
            "app_version",
            "application_version",
            "application_name",
        )
    }


def _public_list(client: DBOSClient) -> list[dict[str, object]]:
    statuses = client.list_workflows(
        workflow_ids=[WORKFLOW_ID],
        load_input=False,
        load_output=False,
        application_name=APP_NAME,
    )
    return [_status_dict(status) for status in statuses]


def _single_status(client: DBOSClient) -> dict[str, object] | None:
    statuses = _public_list(client)
    return statuses[0] if statuses else None


def _wait_for_event(
    process: subprocess.Popen[str], event_name: str, timeout: float = 30
) -> tuple[dict[str, object], list[str]]:
    if process.stdout is None:
        raise RuntimeError("worker stdout was not captured")
    output: list[str] = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None and not output:
            raise RuntimeError(f"worker exited before {event_name}: {process.returncode}")
        remaining = max(0.0, deadline - time.monotonic())
        ready, _, _ = select.select([process.stdout], [], [], min(0.2, remaining))
        if not ready:
            continue
        line = process.stdout.readline()
        if not line:
            continue
        output.append(line)
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed.get("event") == event_name:
            return parsed, output
    raise TimeoutError(f"worker did not emit {event_name}: {''.join(output)}")


def _wait_for_workflow_terminal_event(
    process: subprocess.Popen[str], timeout: float = 30
) -> tuple[dict[str, object], list[str]]:
    if process.stdout is None:
        raise RuntimeError("worker stdout was not captured")
    output: list[str] = []
    deadline = time.monotonic() + timeout
    accepted = {"workflow_result", "workflow_error"}
    while time.monotonic() < deadline:
        if process.poll() is not None and not output:
            raise RuntimeError(f"worker exited before workflow outcome: {process.returncode}")
        remaining = max(0.0, deadline - time.monotonic())
        ready, _, _ = select.select([process.stdout], [], [], min(0.2, remaining))
        if not ready:
            continue
        line = process.stdout.readline()
        if not line:
            continue
        output.append(line)
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed.get("event") in accepted:
            return parsed, output
    raise TimeoutError(f"worker did not emit workflow outcome: {''.join(output)}")


def _start_worker(
    role: str, application_version: str, executor_id: str, *, migrate: bool
) -> tuple[subprocess.Popen[str], list[str]]:
    command = [
        sys.executable,
        str(SCRIPT),
        "worker",
        "--role",
        role,
        "--application-version",
        application_version,
        "--executor-id",
        executor_id,
    ]
    if migrate:
        command.append("--migrate")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=os.environ.copy(),
        start_new_session=True,
    )
    return process, command


def _stop_worker(process: subprocess.Popen[str], *, continued: bool = False) -> str:
    if process.poll() is None:
        if not continued:
            os.killpg(process.pid, signal.SIGCONT)
        os.killpg(process.pid, signal.SIGTERM)
    try:
        output, _ = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        output, _ = process.communicate()
    return str(_redact(output))


def _wait_for_terminal(client: DBOSClient, timeout: float = 30) -> dict[str, object] | None:
    deadline = time.monotonic() + timeout
    terminal = {"SUCCESS", "ERROR", "CANCELLED", "MAX_RECOVERY_ATTEMPTS_EXCEEDED"}
    latest: dict[str, object] | None = None
    while time.monotonic() < deadline:
        latest = _single_status(client)
        if latest is not None and latest.get("status") in terminal:
            return latest
        time.sleep(0.1)
    return latest


def _run_race() -> dict[str, object]:
    server = _effect_server()
    client = DBOSClient(
        system_database_url=os.environ["G03_SYSTEM_DATABASE_URL"],
        application_name=APP_NAME,
        use_listen_notify=True,
    )
    processes: dict[str, subprocess.Popen[str]] = {}
    commands: dict[str, list[str]] = {}
    events: dict[str, object] = {}
    result: dict[str, object] = {
        "probe": "real_dbos_post_effect_pre_checkpoint_zombie_race",
        "workflow_id": WORKFLOW_ID,
        "application_name": APP_NAME,
        "application_version": APP_VERSION,
        "wrong_application_version": WRONG_VERSION,
        "public_api_only": True,
        "system_table_reads_or_writes": False,
        "real_dbos_migrations": True,
    }
    try:
        process, command = _start_worker("a", APP_VERSION, "gate03-race-a", migrate=True)
        processes["a"] = process
        commands["a"] = command
        ready, ready_output = _wait_for_event(process, "ready")
        started, started_output = _wait_for_event(process, "started")
        events["a_ready"] = ready
        events["a_started"] = started
        effect_deadline = time.monotonic() + 30
        while not EFFECT_STATE.first_effect.wait(timeout=0.1):
            if process.poll() is not None:
                raise RuntimeError(f"executor A exited before effect: {process.returncode}")
            if time.monotonic() > effect_deadline:
                raise TimeoutError("executor A did not reach the keyed HTTP effect")

        os.kill(process.pid, signal.SIGSTOP)
        events["a_stop"] = {
            "signal": "SIGSTOP",
            "point": "after_effect_before_http_response_and_step_return",
            "raw_calls_at_stop": EFFECT_STATE.raw_calls,
            "keyed_effects_at_stop": EFFECT_STATE.keyed_effects,
            "worker_output_before_stop": _redact(ready_output + started_output),
        }
        before_wrong = _single_status(client)

        wrong, wrong_command = _start_worker(
            "wrong", WRONG_VERSION, "gate03-race-wrong", migrate=False
        )
        processes["wrong"] = wrong
        commands["wrong"] = wrong_command
        wrong_ready, wrong_output = _wait_for_event(wrong, "ready")
        events["wrong_ready"] = wrong_ready
        time.sleep(0.5)
        after_wrong = _single_status(client)
        events["wrong_version_observation"] = {
            "status_before_wrong_worker": before_wrong,
            "status_after_wrong_worker_start": after_wrong,
            "worker_output": _redact(wrong_output),
            "recovered_by_wrong_version": (
                before_wrong is not None
                and after_wrong is not None
                and after_wrong.get("executor_id") != before_wrong.get("executor_id")
            ),
        }

        same, same_command = _start_worker("b", APP_VERSION, "gate03-race-b", migrate=False)
        processes["same_version_b"] = same
        commands["same_version_b"] = same_command
        same_ready, same_output = _wait_for_event(same, "ready")
        events["same_version_b_ready"] = same_ready

        resumed_handle = client.resume_workflow(WORKFLOW_ID)
        events["public_resume"] = {
            "api": "DBOSClient.resume_workflow",
            "handle_type": type(resumed_handle).__name__,
            "workflow_id": WORKFLOW_ID,
        }
        after_resume = _single_status(client)
        terminal_status = _wait_for_terminal(client)
        events["same_version_b_observation"] = {
            "status_after_public_resume": after_resume,
            "terminal_status": terminal_status,
            "worker_output": _redact(same_output),
        }

        raw_deadline = time.monotonic() + 30
        while EFFECT_STATE.raw_calls < 2 and time.monotonic() < raw_deadline:
            time.sleep(0.05)
        EFFECT_STATE.release_first.set()
        os.kill(process.pid, signal.SIGCONT)
        a_result, a_output = _wait_for_workflow_terminal_event(process, timeout=30)
        events["a_resume_observation"] = {"event": a_result, "worker_output": _redact(a_output)}
        final_status = _single_status(client)

        result.update(
            {
                "observations": events,
                "effect_stub": {
                    "raw_call_count": EFFECT_STATE.raw_calls,
                    "keyed_effect_count": EFFECT_STATE.keyed_effects,
                    "calls": EFFECT_STATE.calls,
                },
                "final_public_status": final_status,
                "same_version_completed": bool(
                    terminal_status and terminal_status.get("status") == "SUCCESS"
                ),
                "wrong_version_did_not_recover": bool(
                    events["wrong_version_observation"]["recovered_by_wrong_version"] is False  # type: ignore[index]
                ),
                "keyed_effect_protected": (
                    EFFECT_STATE.raw_calls == 2 and EFFECT_STATE.keyed_effects == 1
                ),
                "verdict": "OBSERVED_LIMITED_RESULT",
                "limitations": [
                    "This run proves only the observed DBOS 3.0.0 public-API race "
                    "outcome in this topology.",
                    "DBOSClient.resume_workflow is not an expected-executor "
                    "conditional recovery API.",
                    "The probe does not prove safe reaper ownership or general zombie fencing.",
                    "The HTTP stub's keyed response models an idempotency boundary; "
                    "it is not a customer system.",
                ],
            }
        )
    finally:
        EFFECT_STATE.release_first.set()
        for name, process in processes.items():
            if process.poll() is None:
                _stop_worker(process, continued=name == "a")
        client.destroy()
        server.shutdown()
    return result


def run() -> int:
    env_file = ROOT / "deployment/gate-0.3/.env"
    env_file.write_text(
        "G03_DB_USER=gate03\nG03_DB_PASSWORD=gate03_local_only\n"
        "G03_APP_DB=gate03_app\nG03_SYSTEM_DB=gate03_system\n"
    )
    os.environ.update(
        {
            "G03_SYSTEM_DATABASE_URL": f"{SYSTEM_DATABASE_URL}?password=gate03_local_only",
            "G03_APP_DATABASE_URL": f"{APP_DATABASE_URL}?password=gate03_local_only",
        }
    )
    compose = [
        "docker",
        "compose",
        "--env-file",
        str(env_file),
        "-f",
        "deployment/gate-0.3/docker-compose.yml",
    ]
    result: dict[str, object] = {
        "probe": "real_dbos_post_effect_pre_checkpoint_zombie_race",
        "verdict": "REDUCED_FIDELITY",
        "limitations": ["The probe did not start."],
    }
    try:
        up = subprocess.run([*compose, "up", "-d", "--wait"], capture_output=True, text=True)
        if up.returncode != 0:
            result = {
                "probe": "real_dbos_post_effect_pre_checkpoint_zombie_race",
                "verdict": "REDUCED_FIDELITY",
                "failure": "Docker environment did not start",
                "docker_up": {
                    "returncode": up.returncode,
                    "stdout": _redact(up.stdout),
                    "stderr": _redact(up.stderr),
                },
                "limitations": ["No DBOS worker or public resume probe was run."],
            }
        else:
            try:
                result = _run_race()
            except Exception as exc:
                result = {
                    "probe": "real_dbos_post_effect_pre_checkpoint_zombie_race",
                    "verdict": "REDUCED_FIDELITY",
                    "failure": {"type": type(exc).__name__, "message": str(exc)},
                    "limitations": [
                        "The supported public API probe could not complete safely; "
                        "no recovery conclusion is made.",
                        "No private DBOS API or DBOS system-table mutation was used.",
                    ],
                }
    finally:
        down = subprocess.run([*compose, "down", "-v"], capture_output=True, text=True)
        _write(
            "recovery-race-commands.json",
            {
                "runner": [
                    "uv",
                    "run",
                    "python",
                    "deployment/gate-0.3/recovery_race.py",
                    "run",
                ],
                "docker_up": [*compose, "up", "-d", "--wait"],
                "docker_down": [*compose, "down", "-v"],
                "public_apis": ["DBOSClient.list_workflows", "DBOSClient.resume_workflow"],
                "private_dbos_api_or_system_table_mutation": False,
                "docker_down_result": {
                    "returncode": down.returncode,
                    "stdout": _redact(down.stdout),
                    "stderr": _redact(down.stderr),
                },
            },
        )
        _write("recovery-race.json", result)
        env_file.unlink(missing_ok=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "worker"))
    parser.add_argument("--role", choices=("a", "b", "wrong"))
    parser.add_argument("--application-version")
    parser.add_argument("--executor-id")
    parser.add_argument("--migrate", action="store_true")
    args = parser.parse_args()
    if args.command == "worker":
        if not args.role or not args.application_version or not args.executor_id:
            parser.error("worker requires --role, --application-version, and --executor-id")
        asyncio.run(_worker(args))
        return 0
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
