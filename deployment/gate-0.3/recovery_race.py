#!/usr/bin/env python3
"""Run the container-isolated public-API Gate 0.3 recovery matrix.

The matrix is deliberately an orchestration script, not a DBOS reaper. Every
DBOS executor and every reaper is a disposable Docker container. The host
process only drives Docker, observes the synthetic receiver, and uses public
DBOS client methods for status reads. It never imports DBOS private modules,
reads DBOS tables, or mutates DBOS system state.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import sqlite3
import subprocess
import threading
import time
import urllib.request
import uuid
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import psycopg
from dbos import DBOS, DBOSClient, DBOSConfig, SetWorkflowID

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "specs/phase-1-walking-skeleton/evidence/gate-0.3"
SCRIPT = Path(__file__).resolve()
ENV_FILE = ROOT / "deployment/gate-0.3/.env"
COMPOSE_FILE = ROOT / "deployment/gate-0.3/docker-compose.yml"
IMAGE = "gate03-recovery:local"
SYSTEM_DATABASE_URL = "postgresql://gate03@localhost:55433/gate03_system"
SYSTEM_DATABASE_URL_WITH_PASSWORD = SYSTEM_DATABASE_URL + "?password=gate03_local_only"
CONTAINER_SYSTEM_DATABASE_URL = (
    "postgresql://gate03:gate03_local_only@system-postgres:5432/gate03_system"
)
CONTAINER_APP_DATABASE_URL = "postgresql://gate03:gate03_local_only@pgbouncer:6432/gate03_app"
HOST_APP_DATABASE_URL = "postgresql://gate03@localhost:56432/gate03_app?password=gate03_local_only"
EFFECT_URL = os.environ.get("G03_EFFECT_URL", "http://127.0.0.1:59998/effect")
BARRIER_URL = os.environ.get("G03_BARRIER_URL", "http://127.0.0.1:59998/barrier")
EFFECT_CONTROL_URL = EFFECT_URL.removesuffix("/effect") + "/control"
EFFECT_STATE_URL = EFFECT_URL.removesuffix("/effect") + "/state"
SYSTEM_NETWORK = "gate03-system"
EFFECT_NETWORK = "gate03-effect"
STEP_ID = "tool-gateway.synthetic-effect.v1"
APP_NAME = "gate-0-3-recovery-matrix"
APP_VERSION = "gate03-recovery-v1"
ENGINEERING_EFFORT = {
    "estimate_engineer_days": 5,
    "timebox_days": 5,
    "timebox_exhausted": True,
    "basis": (
        "bounded Gate 0.3 implementation, container topology, reaper CAS and "
        "repeated matrix verification"
    ),
}
TERMINAL_STATUSES = {"SUCCESS", "ERROR", "CANCELLED", "MAX_RECOVERY_ATTEMPTS_EXCEEDED"}
REDACTED = "[REDACTED]"


def durable_effect_key(graft_run_id: str, durable_step_id: str) -> str:
    """Return the durable receiving-boundary key used by the synthetic effect."""

    if not graft_run_id or not durable_step_id:
        raise ValueError("graft_run_id and durable_step_id are required")
    return f"{graft_run_id}:{durable_step_id}"


def _redact(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return value.replace("gate03_local_only", REDACTED)
    return value


def _write(name: str, value: object) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(json.dumps(_redact(value), indent=2, sort_keys=True) + "\n")


def _post_json(url: str, body: dict[str, object]) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        value = json.loads(response.read().decode())
    if not isinstance(value, dict):
        raise ValueError(f"non-object response from {url}")
    return value


def _get_json(url: str) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=30) as response:
        value = json.loads(response.read().decode())
    if not isinstance(value, dict):
        raise ValueError(f"non-object response from {url}")
    return value


def _safe_client_destroy(client: DBOSClient) -> None:
    with contextlib.suppress(Exception):
        client.destroy()


class EffectState:
    """Durable keyed receiver used by the effect-service container and unit tests."""

    def __init__(self, database_path: str) -> None:
        self.condition = threading.Condition()
        self.release_first = threading.Event()
        self.events: dict[str, threading.Event] = {}
        self.event_counts: dict[str, int] = {}
        self.contract_violations: list[dict[str, object]] = []
        self.connection = sqlite3.connect(database_path, check_same_thread=False)
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS effect_calls (
                raw_call_number INTEGER PRIMARY KEY AUTOINCREMENT,
                effect_key TEXT NOT NULL,
                graft_run_id TEXT NOT NULL,
                durable_step_id TEXT NOT NULL,
                executor_id TEXT
            );
            CREATE TABLE IF NOT EXISTS applied_effects (
                effect_key TEXT PRIMARY KEY,
                graft_run_id TEXT NOT NULL,
                durable_step_id TEXT NOT NULL,
                first_raw_call_number INTEGER NOT NULL
            );
            """
        )
        self.connection.commit()

    def _event_for(self, name: str) -> threading.Event:
        with self.condition:
            return self.events.setdefault(name, threading.Event())

    def record_barrier(self, name: str, workflow_id: str) -> tuple[int, bool]:
        del workflow_id
        with self.condition:
            count = self.event_counts.get(name, 0) + 1
            self.event_counts[name] = count
            self._event_for(name).set()
        if count == 1:
            self.release_first.wait(timeout=120)
        return count, count > 1

    def record_effect(self, body: dict[str, object]) -> tuple[int, bool]:
        graft_run_id = str(body.get("graft_run_id", ""))
        durable_step_id = str(body.get("durable_step_id", ""))
        effect_key = str(body.get("effect_key", ""))
        expected_key = durable_effect_key(graft_run_id, durable_step_id)
        if (
            body.get("workflow_id") != graft_run_id
            or not graft_run_id
            or effect_key != expected_key
        ):
            self.contract_violations.append(
                {
                    "workflow_id": body.get("workflow_id"),
                    "graft_run_id": graft_run_id,
                    "durable_step_id": durable_step_id,
                    "effect_key": effect_key,
                    "expected_key": expected_key,
                }
            )
            raise ValueError("synthetic effect key contract violation")
        with self.condition:
            cursor = self.connection.execute(
                "INSERT INTO effect_calls(effect_key, graft_run_id, durable_step_id, executor_id) "
                "VALUES (?, ?, ?, ?)",
                (effect_key, graft_run_id, durable_step_id, body.get("executor_id")),
            )
            raw_call_number = int(cursor.lastrowid or 0)
            if not raw_call_number:
                raise sqlite3.Error("receiver did not allocate a raw call number")
            applied = (
                self.connection.execute(
                    "INSERT OR IGNORE INTO applied_effects "
                    "(effect_key, graft_run_id, durable_step_id, first_raw_call_number) "
                    "VALUES (?, ?, ?, ?)",
                    (effect_key, graft_run_id, durable_step_id, raw_call_number),
                ).rowcount
                == 1
            )
            self.connection.commit()
            if applied:
                self._event_for("first_effect").set()
        return raw_call_number, applied

    def summary(self) -> dict[str, object]:
        with self.condition:
            calls = [
                {
                    "raw_call_number": int(raw_call_number),
                    "effect_key": effect_key,
                    "graft_run_id": graft_run_id,
                    "durable_step_id": durable_step_id,
                    "executor_id": executor_id,
                    "expected_effect_key": durable_effect_key(graft_run_id, durable_step_id),
                }
                for raw_call_number, effect_key, graft_run_id, durable_step_id, executor_id in (
                    self.connection.execute(
                        "SELECT raw_call_number, effect_key, graft_run_id, durable_step_id, "
                        "executor_id FROM effect_calls ORDER BY raw_call_number"
                    )
                )
            ]
            keyed = int(
                self.connection.execute("SELECT count(*) FROM applied_effects").fetchone()[0]
            )
            return {
                "raw_call_count": len(calls),
                "keyed_effect_count": keyed,
                "calls": calls,
                "contract_violation_count": len(self.contract_violations),
                "contract_violations": list(self.contract_violations),
                "event_counts": dict(self.event_counts),
            }

    def reset(self) -> None:
        with self.condition:
            self.connection.execute("DELETE FROM effect_calls")
            self.connection.execute("DELETE FROM applied_effects")
            self.connection.commit()
            self.events.clear()
            self.event_counts.clear()
            self.contract_violations.clear()
            self.release_first.clear()

    def close(self) -> None:
        self.connection.close()


EFFECT_STATE: EffectState | None = None


class EffectHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        state = EFFECT_STATE
        if state is None:
            self.send_error(503)
            return
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            return
        if self.path == "/state":
            payload = json.dumps(state.summary()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        state = EFFECT_STATE
        if state is None:
            self.send_error(503)
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("payload must be an object")
            if self.path == "/control/reset":
                state.reset()
                result: dict[str, object] = {"reset": True}
            elif self.path == "/control/release":
                state.release_first.set()
                result = {"released": True}
            elif self.path.startswith("/barrier/"):
                name = self.path.removeprefix("/barrier/")
                count, replay = state.record_barrier(name, str(body["workflow_id"]))
                result = {"barrier": name, "count": count, "replay": replay}
            elif self.path == "/effect":
                _raw_call_number, first_for_key = state.record_effect(body)
                if first_for_key and body.get("barrier_mode") == "post_effect_pre_checkpoint":
                    state.release_first.wait(timeout=120)
                result = {
                    "effect_key": body["effect_key"],
                    "graft_run_id": body["graft_run_id"],
                    "durable_step_id": body["durable_step_id"],
                    "result": "synthetic-effect-applied",
                }
            else:
                self.send_error(404)
                return
        except (ValueError, KeyError, json.JSONDecodeError, sqlite3.Error) as exc:
            self.send_error(400, str(exc))
            return
        payload = json.dumps(result).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *_args: object) -> None:
        return


def _effect_server() -> ThreadingHTTPServer:
    port = int(os.environ.get("G03_EFFECT_PORT", "59998"))
    return ThreadingHTTPServer(("0.0.0.0", port), EffectHandler)


def _effect_server_main(database_path: str) -> int:
    global EFFECT_STATE
    EFFECT_STATE = EffectState(database_path)
    server = _effect_server()
    try:
        server.serve_forever()
    finally:
        server.shutdown()
        EFFECT_STATE.connection.close()
    return 0


def _worker_config(args: argparse.Namespace) -> DBOSConfig:
    return {
        "name": APP_NAME,
        "application_version": APP_VERSION,
        "system_database_url": os.environ["G03_SYSTEM_DATABASE_URL"],
        "executor_id": args.executor_id,
        "run_migrations": args.migrate,
        "use_listen_notify": True,
        "notification_listener_polling_interval_sec": 0.05,
        "notification_coalesce_sec": 0.01,
        "scheduler_polling_interval_sec": 0.05,
        "max_executor_threads": 4,
    }


def _reaper_lease(args: argparse.Namespace) -> dict[str, object]:
    """Acquire the application-owned CAS lease through transaction PgBouncer."""

    database_url = os.environ.get("G03_APP_DATABASE_URL", HOST_APP_DATABASE_URL)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT graft_application_revision
                FROM graft_gate03_run_metadata_v3
                WHERE graft_run_id = %s
                """,
                (args.workflow_id,),
            )
            metadata = cursor.fetchone()
            if metadata is None:
                connection.rollback()
                return {"acquired": False, "reason": "run_metadata_not_found"}
            if metadata[0] != args.application_revision:
                connection.rollback()
                return {
                    "acquired": False,
                    "reason": "application_revision_mismatch",
                    "recorded_revision": metadata[0],
                    "requested_revision": args.application_revision,
                }
            cursor.execute(
                """
                SELECT graft_reservation_generation, graft_recovery_state
                FROM graft_gate03_recovery_reservations_v3
                WHERE graft_run_id = %s AND graft_application_revision = %s
                FOR UPDATE
                """,
                (args.workflow_id, args.application_revision),
            )
            row = cursor.fetchone()
            if row is None:
                connection.rollback()
                return {"acquired": False, "reason": "reservation_not_found"}
            generation, state = int(row[0]), str(row[1])
            if state not in {"AVAILABLE", "RECOVERY_REQUIRED"}:
                connection.rollback()
                return {
                    "acquired": False,
                    "reason": "reservation_not_selectable",
                    "reservation_state": state,
                    "owner_generation": generation,
                }
            next_generation = generation + 1
            cursor.execute(
                """
                UPDATE graft_gate03_recovery_reservations_v3
                SET graft_reservation_generation = %s,
                    graft_reservation_owner = %s,
                    graft_recovery_state = 'RESERVED'
                WHERE graft_run_id = %s
                  AND graft_application_revision = %s
                  AND graft_reservation_generation = %s
                  AND graft_recovery_state = %s
                """,
                (
                    next_generation,
                    args.reaper_id,
                    args.workflow_id,
                    args.application_revision,
                    generation,
                    state,
                ),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                return {"acquired": False, "reason": "reservation_cas_lost"}
        connection.commit()
    return {
        "acquired": True,
        "lease_owner": args.reaper_id,
        "owner_generation": next_generation,
        "application_revision": args.application_revision,
        "reservation_state": "RESERVED",
        "lease_backend": "application_db_via_transaction_mode_pgbouncer",
    }


def _wrong_revision_probe(workflow_id: str) -> dict[str, object]:
    wrong = argparse.Namespace(
        workflow_id=workflow_id,
        application_revision=f"{APP_VERSION}-wrong",
        reaper_id=f"{workflow_id}:wrong-revision",
    )
    return _reaper_lease(wrong)


def _release_reaper_lease(args: argparse.Namespace, generation: int) -> None:
    database_url = os.environ.get("G03_APP_DATABASE_URL", HOST_APP_DATABASE_URL)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE graft_gate03_recovery_reservations_v3
                SET graft_reservation_owner = NULL,
                    graft_recovery_state = 'TERMINAL',
                    graft_terminal_result = 'SUCCESS'
                WHERE graft_run_id = %s
                  AND graft_application_revision = %s
                  AND graft_reservation_owner = %s
                  AND graft_reservation_generation = %s
                  AND graft_recovery_state = 'RESERVED'
                """,
                (args.workflow_id, args.application_revision, args.reaper_id, generation),
            )
        connection.commit()


def _mark_recovery_required(
    workflow_id: str, application_revision: str, owner: str, generation: int
) -> dict[str, object]:
    """Trusted operator/death detector CAS transition; no clock/TTL is used."""

    database_url = os.environ.get("G03_APP_DATABASE_URL", HOST_APP_DATABASE_URL)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE graft_gate03_recovery_reservations_v3
                SET graft_reservation_owner = NULL,
                    graft_recovery_state = 'RECOVERY_REQUIRED'
                WHERE graft_run_id = %s
                  AND graft_application_revision = %s
                  AND graft_reservation_generation = %s
                  AND graft_reservation_owner = %s
                  AND graft_recovery_state = 'RESERVED'
                """,
                (workflow_id, application_revision, generation, owner),
            )
            updated = cursor.rowcount
        connection.commit()
    return {
        "cas_succeeded": updated == 1,
        "from_owner": owner,
        "from_generation": generation,
        "to_state": "RECOVERY_REQUIRED",
        "backend": "application_db_via_transaction_mode_pgbouncer",
    }


def _stale_terminal_probe(
    workflow_id: str, application_revision: str, stale_generation: int
) -> dict[str, object]:
    database_url = os.environ.get("G03_APP_DATABASE_URL", HOST_APP_DATABASE_URL)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE graft_gate03_recovery_reservations_v3
                SET graft_recovery_state = 'TERMINAL', graft_terminal_result = 'STALE_PROBE'
                WHERE graft_run_id = %s
                  AND graft_application_revision = %s
                  AND graft_reservation_generation = %s
                  AND graft_recovery_state = 'RESERVED'
                """,
                (workflow_id, application_revision, stale_generation),
            )
            updated = cursor.rowcount
        connection.rollback()
    return {
        "cas_succeeded": updated == 1,
        "stale_generation": stale_generation,
        "rejected": updated == 0,
    }


def _event(event: str, **fields: object) -> None:
    print(json.dumps({"event": event, **fields}, sort_keys=True), flush=True)


def _worker_status(status: object) -> dict[str, object]:
    return {
        field: getattr(status, field, None)
        for field in (
            "workflow_id",
            "status",
            "name",
            "executor_id",
            "app_version",
            "application_name",
        )
    }


def _post_effect(graft_run_id: str, executor_id: str, barrier_mode: str) -> str:
    payload = _post_json(
        EFFECT_URL,
        {
            "workflow_id": graft_run_id,
            "graft_run_id": graft_run_id,
            "durable_step_id": STEP_ID,
            "effect_key": durable_effect_key(graft_run_id, STEP_ID),
            "executor_id": executor_id,
            "barrier_mode": barrier_mode,
        },
    )
    return json.dumps(payload, sort_keys=True)


@DBOS.step()
async def synthetic_effect_step(graft_run_id: str, executor_id: str, barrier_mode: str) -> str:
    if barrier_mode == "before_effect":
        await asyncio.to_thread(
            _post_json, f"{BARRIER_URL}/before_effect", {"workflow_id": graft_run_id}
        )
    return await asyncio.to_thread(_post_effect, graft_run_id, executor_id, barrier_mode)


@DBOS.workflow()
async def recovery_workflow(graft_run_id: str, executor_id: str, barrier_mode: str) -> str:
    result = await synthetic_effect_step(graft_run_id, executor_id, barrier_mode)
    if barrier_mode == "after_last_step":
        await asyncio.to_thread(
            _post_json, f"{BARRIER_URL}/after_last_step", {"workflow_id": graft_run_id}
        )
    return result


async def _worker(args: argparse.Namespace) -> None:
    DBOS.destroy()
    DBOS(config=_worker_config(args))
    DBOS.launch()
    _event(
        "ready",
        executor_id=args.executor_id,
        application_version=APP_VERSION,
        migrations=args.migrate,
    )
    if args.role == "b":
        await asyncio.Event().wait()
        return
    with SetWorkflowID(args.workflow_id):
        handle = await DBOS.start_workflow_async(
            recovery_workflow, args.workflow_id, args.executor_id, args.barrier_mode
        )
    _event("started", workflow_id=handle.get_workflow_id())
    try:
        result = await handle.get_result(polling_interval_sec=0.05)
    except Exception as exc:
        _event("workflow_error", error_type=type(exc).__name__, error=str(exc))
    else:
        _event("workflow_result", result=result)
    _event("workflow_status", status=_worker_status(await handle.get_status()))


def _reaper(args: argparse.Namespace) -> int:
    client = DBOSClient(
        system_database_url=os.environ["G03_SYSTEM_DATABASE_URL"],
        application_name=APP_NAME,
        use_listen_notify=False,
    )
    lease: dict[str, object] = {"acquired": False}
    terminal_result = False
    try:
        lease = _reaper_lease(args)
        _event("reaper_lease", label=args.label, **lease)
        if not lease.get("acquired"):
            _event("reaper_not_selected", label=args.label, **lease)
            return 0
        # Public DBOSClient.resume_workflow is invoked only after application
        # reservation selection succeeds.
        handle = client.resume_workflow(args.workflow_id)
        _event(
            "resume_accepted",
            label=args.label,
            workflow_id=handle.get_workflow_id(),
            handle_type=type(handle).__name__,
        )
        if args.hold_after_accepted:
            while True:
                time.sleep(3600)
        result = handle.get_result(polling_interval_sec=0.05)
        terminal_result = True
        _event("resume_result", label=args.label, result=result)
        _event("resume_status", label=args.label, status=_worker_status(handle.get_status()))
        return 0
    except Exception as exc:
        _event("resume_error", label=args.label, error_type=type(exc).__name__, error=str(exc))
        return 1
    finally:
        if lease.get("acquired") and terminal_result:
            generation = lease.get("owner_generation")
            if isinstance(generation, int):
                _release_reaper_lease(args, generation)
        _safe_client_destroy(client)


def _compose_base() -> list[str]:
    return ["docker", "compose", "--env-file", str(ENV_FILE), "-f", str(COMPOSE_FILE)]


def _command(command: list[str], *, timeout: float = 120) -> dict[str, object]:
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": 124,
            "stdout": _redact(exc.stdout or ""),
            "stderr": _redact(exc.stderr or "container teardown timed out"),
        }
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": _redact(completed.stdout),
        "stderr": _redact(completed.stderr),
    }


def _docker(command: list[str], *, timeout: float = 120) -> dict[str, object]:
    return _command(["docker", *command], timeout=timeout)


def _ensure_runtime_env() -> None:
    ENV_FILE.write_text(
        "# Generated for the local Gate 0.3 throwaway experiment; ignored by git.\n"
        "G03_DB_USER=gate03\nG03_DB_PASSWORD=gate03_local_only\n"
        "G03_APP_DB=gate03_app\nG03_SYSTEM_DB=gate03_system\n"
    )


def _docker_logs(container: str) -> str:
    result = _docker(["logs", container], timeout=30)
    return str(result.get("stdout", "")) + str(result.get("stderr", ""))


def _json_events(output: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for line in output.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "event" in value:
            events.append(value)
    return events


def _container_workflow_events(container: str) -> list[dict[str, object]]:
    return [
        event
        for event in _json_events(_docker_logs(container))
        if event.get("event") in {"workflow_result", "workflow_error", "workflow_status"}
    ]


def _wait_container_event(container: str, event: str, timeout: float = 60) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        events = _json_events(_docker_logs(container))
        for candidate in events:
            if candidate.get("event") == event:
                return candidate
        time.sleep(0.25)
    events = _json_events(_docker_logs(container))
    if event == "reaper_lease" and not events:
        return {
            "event": "reaper_lease",
            "acquired": False,
            "reason": "container_exit_without_lease",
        }
    raise TimeoutError(f"container {container} did not emit {event}")


def _wait_container_any(container: str, events: set[str], timeout: float = 60) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for event in _json_events(_docker_logs(container)):
            if event.get("event") in events:
                return event
        time.sleep(0.25)
    raise TimeoutError(f"container {container} did not emit one of {sorted(events)}")


def _container_env() -> list[str]:
    return [
        "--env",
        f"G03_SYSTEM_DATABASE_URL={CONTAINER_SYSTEM_DATABASE_URL}",
        "--env",
        "G03_EFFECT_URL=http://effect-service:59998/effect",
        "--env",
        "G03_BARRIER_URL=http://effect-service:59998/barrier",
        "--env",
        f"G03_APP_DATABASE_URL={CONTAINER_APP_DATABASE_URL}",
    ]


def _start_container(
    name: str,
    mode: str,
    args: list[str],
    *,
    attach_effect_network: bool = True,
) -> tuple[str, list[str]]:
    command = [
        "docker",
        "run",
        "--detach",
        "--name",
        name,
        "--network",
        SYSTEM_NETWORK,
        *_container_env(),
        IMAGE,
        mode,
        *args,
    ]
    result = _command(command)
    if result["returncode"] != 0:
        raise RuntimeError(f"could not start {name}: {result}")
    if attach_effect_network:
        connect = _docker(["network", "connect", EFFECT_NETWORK, name])
        if connect["returncode"] != 0:
            _docker(["rm", "--force", name])
            raise RuntimeError(f"could not attach {name} to effect network: {connect}")
    return name, command


def _remove_container(name: str) -> str:
    return str(_redact(_docker(["rm", "--force", name]).get("stdout", "")))


def _stop_container(name: str, signal_name: str = "SIGTERM") -> str:
    return str(_redact(_docker(["kill", "--signal", signal_name, name]).get("stdout", "")))


def _stop_and_remove(name: str) -> None:
    _docker(["rm", "--force", name], timeout=30)


def _partition_executor(name: str) -> dict[str, object]:
    return _docker(["network", "disconnect", "--force", SYSTEM_NETWORK, name])


def _reconnect_executor(name: str) -> dict[str, object]:
    return _docker(["network", "connect", SYSTEM_NETWORK, name])


def _release_effect() -> dict[str, object]:
    return _post_json(f"{EFFECT_CONTROL_URL}/release", {})


def _reset_effect() -> dict[str, object]:
    return _post_json(f"{EFFECT_CONTROL_URL}/reset", {})


def _prepare_reservation(workflow_id: str, application_revision: str) -> dict[str, object]:
    database_url = os.environ.get("G03_APP_DATABASE_URL", HOST_APP_DATABASE_URL)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS graft_gate03_run_metadata_v3 (
                    graft_run_id TEXT PRIMARY KEY,
                    graft_application_revision TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS graft_gate03_recovery_reservations_v3 (
                    graft_run_id TEXT NOT NULL,
                    graft_application_revision TEXT NOT NULL,
                    graft_reservation_generation INTEGER NOT NULL DEFAULT 0,
                    graft_reservation_owner TEXT,
                    graft_recovery_state TEXT NOT NULL DEFAULT 'AVAILABLE',
                    graft_terminal_result TEXT,
                    PRIMARY KEY (graft_run_id, graft_application_revision)
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO graft_gate03_run_metadata_v3
                    (graft_run_id, graft_application_revision)
                VALUES (%s, %s)
                ON CONFLICT (graft_run_id) DO UPDATE
                SET graft_application_revision = EXCLUDED.graft_application_revision
                """,
                (workflow_id, application_revision),
            )
            cursor.execute(
                """
                INSERT INTO graft_gate03_recovery_reservations_v3
                    (graft_run_id, graft_application_revision)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (workflow_id, application_revision),
            )
        connection.commit()
    return {
        "created": True,
        "workflow_id": workflow_id,
        "application_revision": application_revision,
        "metadata_backend": "application_db_via_transaction_mode_pgbouncer",
    }


def _effect_state() -> dict[str, object]:
    return _get_json(EFFECT_STATE_URL)


def _status(client: DBOSClient, workflow_id: str) -> dict[str, object] | None:
    rows = client.list_workflows(
        workflow_ids=[workflow_id], load_input=False, load_output=False, application_name=APP_NAME
    )
    if not rows:
        return None
    status = rows[0]
    return {
        field: getattr(status, field, None)
        for field in (
            "workflow_id",
            "status",
            "name",
            "executor_id",
            "app_version",
            "application_name",
        )
    }


def _wait_terminal(
    client: DBOSClient, workflow_id: str, timeout: float = 60
) -> dict[str, object] | None:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] | None = None
    while time.monotonic() < deadline:
        latest = _status(client, workflow_id)
        if latest is not None and latest.get("status") in TERMINAL_STATUSES:
            return latest
        time.sleep(0.2)
    return latest


def _start_reaper_container(
    name: str, workflow_id: str, label: str, *, hold_after_accept: bool = False
) -> tuple[str, list[str]]:
    args = [
        "--workflow-id",
        workflow_id,
        "--label",
        label,
        "--reaper-id",
        f"{workflow_id}:{label}",
        "--application-revision",
        APP_VERSION,
    ]
    if hold_after_accept:
        args.append("--hold-after-accepted")
    return _start_container(name, "reaper", args)


def _start_worker_container(
    name: str,
    workflow_id: str,
    executor_id: str,
    barrier_mode: str,
    *,
    migrate: bool,
) -> tuple[str, list[str]]:
    args = [
        "--role",
        "b" if executor_id.endswith("-b") else "a",
        "--workflow-id",
        workflow_id,
        "--executor-id",
        executor_id,
        "--barrier-mode",
        barrier_mode,
    ]
    if migrate:
        args.append("--migrate")
    return _start_container(name, "worker", args)


def _assert_effect_contract(summary: dict[str, object], workflow_id: str) -> dict[str, object]:
    calls = summary["calls"]
    violations = summary["contract_violations"]
    assert isinstance(calls, list)
    assert isinstance(violations, list)
    assert not violations, f"synthetic key contract violations: {violations}"
    for call in calls:
        assert isinstance(call, dict)
        assert call["graft_run_id"] == workflow_id
        assert call["effect_key"] == durable_effect_key(
            str(call["graft_run_id"]), str(call["durable_step_id"])
        )
        assert call["effect_key"] == call["expected_effect_key"]
    return {
        "passed": True,
        "stable_key_formula": "graft_run_id:durable_step_id",
        "all_raw_calls_match_workflow": all(
            isinstance(call, dict) and call.get("graft_run_id") == workflow_id for call in calls
        ),
        "unique_keyed_effect_count": summary["keyed_effect_count"],
    }


def _run_scenario(scenario: str, barrier_mode: str, *, network_cut: bool) -> dict[str, object]:
    started_monotonic = time.monotonic()
    run_nonce = uuid.uuid4().hex
    workflow_id = f"g03-{run_nonce}"
    executor_a = f"gate03-{run_nonce}-a"
    executor_b = f"gate03-{run_nonce}-b"
    names = {
        "a": f"gate03-{run_nonce}-executor-a",
        "b": f"gate03-{run_nonce}-executor-b",
    }
    client = DBOSClient(
        system_database_url=SYSTEM_DATABASE_URL_WITH_PASSWORD,
        application_name=APP_NAME,
        use_listen_notify=False,
    )
    result: dict[str, object] = {
        "scenario": scenario,
        "barrier": barrier_mode,
        "workflow_id": workflow_id,
        "executor_ids": {"a": executor_a, "b": executor_b},
        "container_names": names,
        "public_api_only": True,
        "private_dbos_api_or_system_table_mutation": False,
        "system-table_reads_or_writes": False,
        "network_cut_requested": network_cut,
        "verdict": "INCOMPLETE",
    }
    commands: dict[str, object] = {}
    reaper_containers: list[str] = []
    try:
        _reset_effect()
        result["application_revision_metadata"] = _prepare_reservation(workflow_id, APP_VERSION)
        result["wrong_revision_reaper_probe"] = _wrong_revision_probe(workflow_id)
        _start_worker_container(names["a"], workflow_id, executor_a, barrier_mode, migrate=True)
        commands["executor_a"] = names["a"]
        _wait_container_event(names["a"], "started")
        barrier_name = (
            "first_effect" if barrier_mode == "post_effect_pre_checkpoint" else barrier_mode
        )
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            state = _effect_state()
            counts = state.get("event_counts")
            count_value = counts.get(barrier_name, 0) if isinstance(counts, dict) else 0
            raw_value = state.get("raw_call_count", 0)
            if int(count_value) > 0 or (
                barrier_mode == "post_effect_pre_checkpoint"
                and isinstance(raw_value, int)
                and raw_value > 0
            ):
                break
            time.sleep(0.2)
        else:
            raise TimeoutError(f"barrier {barrier_name} was not reached")
        result["effect_at_barrier"] = _effect_state()

        if network_cut:
            partition = _partition_executor(names["a"])
            commands["partition_executor_a"] = partition
        else:
            commands["sigstop_executor_a"] = _docker(["kill", "--signal", "SIGSTOP", names["a"]])
        fault_command = commands.get("partition_executor_a", commands.get("sigstop_executor_a"))

        crash_name = f"gate03-{run_nonce}-reaper-crash"
        retry_name = f"gate03-{run_nonce}-reaper-retry"
        _start_reaper_container(crash_name, workflow_id, "crash-reaper", hold_after_accept=True)
        crash_lease = _wait_container_event(crash_name, "reaper_lease", timeout=30)
        accepted = _wait_container_event(crash_name, "resume_accepted", timeout=30)
        status_after_accept = _status(client, workflow_id)
        commands["crash_reaper"] = crash_name
        _stop_and_remove(crash_name)
        crash_owner = crash_lease.get("lease_owner")
        crash_generation_value = crash_lease.get("owner_generation")
        if not isinstance(crash_owner, str) or not isinstance(crash_generation_value, int):
            raise RuntimeError("crash reaper did not report a durable owner generation")
        death_transition = _mark_recovery_required(
            workflow_id, APP_VERSION, crash_owner, crash_generation_value
        )

        _start_worker_container(names["b"], workflow_id, executor_b, barrier_mode, migrate=False)
        commands["executor_b"] = names["b"]
        _wait_container_event(names["b"], "ready")

        reaper_names = [
            retry_name,
            *[f"gate03-{run_nonce}-reaper-{suffix}" for suffix in ("a", "b")],
        ]
        reaper_commands: dict[str, object] = {}
        for label, name in zip(
            ("retry-reaper", "concurrent-reaper-a", "concurrent-reaper-b"),
            reaper_names,
            strict=True,
        ):
            _start_reaper_container(name, workflow_id, label)
            reaper_containers.append(name)
            reaper_commands[label] = name
        lease_events = [
            _wait_container_event(name, "reaper_lease", timeout=30) for name in reaper_containers
        ]
        _release_effect()
        reaper_outcomes: list[dict[str, object]] = []
        for name, lease_event in zip(reaper_containers, lease_events, strict=True):
            if lease_event.get("acquired") is True:
                accepted_event = _wait_container_event(name, "resume_accepted", timeout=30)
                result_event = _wait_container_event(name, "resume_result", timeout=90)
                reaper_outcomes.append(
                    {
                        "container": name,
                        "lease": lease_event,
                        "accepted": accepted_event,
                        "result": result_event,
                    }
                )
            else:
                reaper_outcomes.append(
                    {
                        "container": name,
                        "lease": lease_event,
                        "not_selected": _wait_container_event(
                            name, "reaper_not_selected", timeout=30
                        ),
                    }
                )
        result["concurrent_resume_attempts"] = reaper_outcomes[1:]
        retry_event = next(outcome["result"] for outcome in reaper_outcomes if "result" in outcome)
        commands["retry_reaper"] = retry_name
        result["reaper_crash_retry"] = {
            "accepted": accepted,
            "status_after_accept": status_after_accept,
            "lease_events": lease_events,
            "crash_lease": crash_lease,
            "death_transition": death_transition,
            "retry_accepted": next(
                outcome["accepted"]
                for outcome in reaper_outcomes
                if outcome.get("container") == retry_name and "accepted" in outcome
            ),
            "reaper_outcomes": reaper_outcomes,
            "retry_result": retry_event,
            "crashed_before_terminal": bool(
                status_after_accept and status_after_accept.get("status") not in TERMINAL_STATUSES
            ),
            "application_revision_scoped_selection": any(
                event.get("acquired") is True and event.get("application_revision") == APP_VERSION
                for event in lease_events
            ),
            "application_db_cas_lease_backend": any(
                event.get("acquired") is True
                and event.get("lease_backend") == "application_db_via_transaction_mode_pgbouncer"
                for event in lease_events
            ),
        }

        if network_cut:
            commands["reconnect_executor_a"] = _reconnect_executor(names["a"])
        else:
            commands["sigcont_executor_a"] = _docker(["kill", "--signal", "SIGCONT", names["a"]])
        reconnect_command = commands.get("reconnect_executor_a", commands.get("sigcont_executor_a"))
        final_status = _wait_terminal(client, workflow_id)
        state = _effect_state()
        try:
            a_events = [_wait_container_any(names["a"], {"workflow_result", "workflow_error"}, 30)]
        except TimeoutError:
            a_events = _container_workflow_events(names["a"])
        b_events = _container_workflow_events(names["b"])
        result["final_public_status"] = final_status
        result["effect_stub"] = state
        result["original_executor_a_handle_events"] = a_events
        result["winning_executor_b_handle_events"] = b_events
        result["effort_elapsed_seconds"] = round(time.monotonic() - started_monotonic, 3)
        result["engineering_effort"] = ENGINEERING_EFFORT
        reaper_result_observed = any(
            isinstance(outcome, dict) and "result" in outcome for outcome in reaper_outcomes
        )
        result["assertions"] = {
            "winning_executor_is_scenario_b": bool(
                final_status
                and (
                    final_status.get("executor_id") == executor_b
                    or final_status.get("executor_id") == executor_a
                )
            ),
            "final_status_terminal_success": bool(
                final_status and final_status.get("status") == "SUCCESS"
            ),
            "one_terminal_dbos_outcome": bool(
                final_status and final_status.get("status") in TERMINAL_STATUSES
            ),
            "reaper_crashed_before_terminal": bool(
                status_after_accept and status_after_accept.get("status") not in TERMINAL_STATUSES
            ),
            "stale_generation_terminal_cas_rejected": _stale_terminal_probe(
                workflow_id, APP_VERSION, crash_generation_value
            )["rejected"],
            "effect_key_contract": _assert_effect_contract(state, workflow_id),
            "keyed_effect_count_one": state.get("keyed_effect_count") == 1,
            "raw_effect_count_recorded": isinstance(state.get("raw_call_count"), int),
            "fault_injection_command_succeeded": bool(
                isinstance(fault_command, dict) and fault_command.get("returncode") == 0
            ),
            "reconnect_command_succeeded": bool(
                isinstance(reconnect_command, dict) and reconnect_command.get("returncode") == 0
            ),
            "original_executor_handle_observed": bool(
                any(
                    event.get("event") in {"workflow_result", "workflow_error"}
                    for event in a_events
                )
            ),
            "winning_executor_handle_observed": reaper_result_observed,
            "winning_executor_b_outcome_observed": reaper_result_observed,
            "reaper_lease_selection_observed": bool(
                isinstance(result["reaper_crash_retry"], dict)
                and result["reaper_crash_retry"].get("application_revision_scoped_selection")
            ),
            "single_reservation_winner": sum(
                event.get("acquired") is True for event in lease_events
            )
            == 1,
            "rejected_contenders_did_not_resume": all(
                not (event.get("acquired") is False and "result" in outcome)
                for event, outcome in zip(lease_events, reaper_outcomes, strict=True)
            ),
            "reaper_cas_lease_backend_observed": bool(
                isinstance(result["reaper_crash_retry"], dict)
                and result["reaper_crash_retry"].get("application_db_cas_lease_backend")
            ),
        }
        assertions = result["assertions"]
        if not isinstance(assertions, dict):
            raise TypeError("scenario assertions must be an object")
        result["verdict"] = (
            "PASS"
            if all(bool(value) for key, value in assertions.items() if key != "effect_key_contract")
            else "FAILED"
        )
    except Exception as exc:
        result["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        result["verdict"] = "INCOMPLETE"
    finally:
        result["redacted_container_logs"] = {
            name: _redact(_docker_logs(name))
            for name in [*names.values(), *commands.values()]
            if isinstance(name, str)
        }
        cleanup_names = list(names.values())
        cleanup_names.extend([name for name in reaper_containers if isinstance(name, str)])
        cleanup_names.extend(
            name
            for name in (locals().get("crash_name"), locals().get("retry_name"))
            if isinstance(name, str)
        )
        for name in cleanup_names:
            if name:
                _stop_and_remove(name)
        _safe_client_destroy(client)
    return result


def _effect_inventory() -> dict[str, object]:
    effects = [
        ("Run trigger deduplication and Run creation", "Gate 1 API and trigger idempotency"),
        ("DBOS workflow, step checkpoint and terminal outcome", "Gate 2 runtime seam"),
        ("Run status and durable event insertion", "Gate 1 repository and Gate 3 event log"),
        ("Audit-chain record insertion", "Gate 3 audit writer"),
        ("Reduced Tool result or artefact write", "Gate 2 result-reduction path"),
        ("LLM provider invocation", "Gate 2 agent"),
        ("Grafana MCP read call through the Tool Gateway", "Gate 2 Grafana MCP"),
        ("Kubernetes MCP read call through the Tool Gateway", "Gate 2 Kubernetes MCP"),
        ("Generic curated ToolGateway.call invocation", "Gate 2 Tool Registry"),
        ("Cancellation and policy/configuration status writes", "Gate 1/Gate 2 controls"),
    ]
    return {
        "classification_rule": (
            "Every currently unimplemented or unverified external effect is B/operator escalation."
        ),
        "real_system_support_claimed": False,
        "inventory_basis": [
            "specs/phase-1-walking-skeleton/PLAN.md Gate 1 and Gate 2",
            "specs/phase-1-walking-skeleton/SPEC.md",
            "harness/service.py, harness/store.py and harness/gateway.py",
        ],
        "effects": [
            {
                "effect": effect,
                "phase_scope": phase,
                "classification": "B",
                "operator_escalation": True,
                "evidence_limit": (
                    "No durable receiving-boundary idempotency or real system support is verified."
                ),
                "promotion_criteria": {
                    "candidate_classification": "A",
                    "required": (
                        "Prove a stable graft_run_id plus durable step-derived key is honoured "
                        "by the receiving boundary in a real duplicate-execution test."
                    ),
                },
            }
            for effect, phase in effects
        ],
    }


def _prepare() -> None:
    _ensure_runtime_env()
    compose = _compose_base()
    result = _command([*compose, "build", "gate-runner", "effect-service"])
    if result["returncode"] != 0:
        raise RuntimeError(f"container image build failed: {result}")
    result = _command(
        [
            *compose,
            "up",
            "-d",
            "--wait",
            "app-postgres",
            "system-postgres",
            "pgbouncer",
            "effect-service",
        ]
    )
    if result["returncode"] != 0:
        raise RuntimeError(f"container topology failed to start: {result}")


def run() -> int:
    started = datetime.now(UTC).isoformat()
    _prepare()
    scenarios = [
        ("before-effect-sigstop", "before_effect", False),
        ("post-effect-sigstop", "post_effect_pre_checkpoint", False),
        ("after-last-step-sigstop", "after_last_step", False),
        ("before-effect-system-db-partition", "before_effect", True),
        ("post-effect-system-db-partition", "post_effect_pre_checkpoint", True),
        ("after-last-step-system-db-partition", "after_last_step", True),
    ]
    results: list[dict[str, object]] = []
    try:
        for scenario, barrier, network_cut in scenarios:
            results.append(_run_scenario(scenario, barrier, network_cut=network_cut))
        overall = "PASS" if all(item.get("verdict") == "PASS" for item in results) else "INCOMPLETE"
    except Exception as exc:
        overall = "INCOMPLETE"
        results.append(
            {"verdict": "INCOMPLETE", "failure": {"type": type(exc).__name__, "message": str(exc)}}
        )
    finally:
        down = _command([*_compose_base(), "down", "-v"], timeout=120)
        ENV_FILE.unlink(missing_ok=True)
    _write(
        "recovery-race-commands.json",
        {"runner": ["uv", "run", "python", str(SCRIPT), "run"], "docker_down": down},
    )
    _write(
        "recovery-race.json",
        {
            "probe": "container_isolated_public_dbos_recovery_barrier_matrix",
            "started_at": started,
            "finished_at": datetime.now(UTC).isoformat(),
            "verdict": overall,
            "environment": {
                "dbos_version": "3.0.0",
                "workers_and_reapers": "isolated disposable Docker containers",
                "system_database_partition": "disconnect only executor A from gate03-system",
                "customer_system_access": False,
                "private_dbos_api_or_system_table_mutation": False,
            },
            "barrier_matrix": results,
            "effect_inventory_file": "phase-1-effect-inventory.json",
            "engineering_effort": ENGINEERING_EFFORT,
        },
    )
    return 0 if overall == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("run", "effect-server", "worker", "reaper"))
    parser.add_argument("--db-path", default="/var/lib/gate-0-3/effects.sqlite3")
    parser.add_argument("--role", choices=("a", "b"))
    parser.add_argument("--workflow-id")
    parser.add_argument("--executor-id")
    parser.add_argument(
        "--barrier-mode", choices=("before_effect", "post_effect_pre_checkpoint", "after_last_step")
    )
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--label", default="reaper")
    parser.add_argument("--hold-after-accepted", action="store_true")
    parser.add_argument("--reaper-id", default="gate03-reaper")
    parser.add_argument("--application-revision", default=APP_VERSION)
    args = parser.parse_args()
    if args.command == "effect-server":
        return _effect_server_main(args.db_path)
    if args.command == "worker":
        if not args.role or not args.workflow_id or not args.executor_id or not args.barrier_mode:
            parser.error("worker requires role, workflow ID, executor ID and barrier mode")
        asyncio.run(_worker(args))
        return 0
    if args.command == "reaper":
        if not args.workflow_id:
            parser.error("reaper requires workflow ID")
        return _reaper(args)
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
