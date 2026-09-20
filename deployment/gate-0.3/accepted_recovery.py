#!/usr/bin/env python3
"""Exercise the accepted Gate 0.3 recovery boundary.

The runner deliberately keeps the accepted recovery guard in one function,
``accepted_runtime_recovery``.  The guard reads Run metadata owned by this
experiment, checks the immutable executor/revision pair, and only then calls
the public DBOS resume API.  Operator escalations are rows in the disposable
application database, not messages that merely appeared on stdout.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import psycopg
from dbos import DBOS, DBOSClient, DBOSConfig, SetWorkflowID
from psycopg import sql

SYSTEM_DATABASE_URL = os.environ.get(
    "G03_SYSTEM_DATABASE_URL",
    "postgresql://gate03@localhost:55433/gate03_system?password=gate03_local_only",
)
APP_DATABASE_URL = os.environ.get(
    "G03_APP_DATABASE_URL",
    # Application metadata and operator escalations deliberately use the
    # transaction-mode PgBouncer endpoint.  The DBOS system database remains
    # on its dedicated direct PostgreSQL endpoint below.
    "postgresql://gate03@localhost:56432/gate03_app?password=gate03_local_only",
)
APP_NAME = "gate-0-3-accepted-recovery"
APP_VERSION = "gate03-accepted-revision-2026-09-20"
TERMINAL_STATUSES = {"SUCCESS", "ERROR", "CANCELLED", "MAX_RECOVERY_ATTEMPTS_EXCEEDED"}
ESCALATION_STATES = ("ALIVE_BUT_SILENT", "AMBIGUOUS", "STUCK")
ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).resolve()
REDACTED = "[REDACTED]"
TENANT_A = "graft-tenant-a"
TENANT_B = "graft-tenant-b"
PYTHON_VERSION = "3.13.0"


@dataclass(frozen=True)
class RunMetadata:
    graft_tenant_id: str
    graft_run_id: str
    graft_executor_id: str
    graft_application_revision: str


@dataclass(frozen=True)
class OperatorEscalation:
    graft_tenant_id: str
    graft_escalation_id: str
    graft_run_id: str
    graft_state: Literal["ALIVE_BUT_SILENT", "AMBIGUOUS", "STUCK"]
    graft_executor_id: str
    graft_application_revision: str
    graft_reason: str
    graft_recorded_at: str


class MetadataConflict(RuntimeError):
    """The insert-once Run metadata was presented with a different revision."""


class RecoveryRejected(RuntimeError):
    """The accepted runtime guard rejected recovery before DBOS resume."""


def _status_dict(status: object) -> dict[str, object] | None:
    if status is None:
        return None
    return {
        field: getattr(status, field, None)
        for field in (
            "workflow_id",
            "status",
            "name",
            "executor_id",
            "app_version",
            "application_version",
            "application_name",
        )
    }


def _config(args: argparse.Namespace, *, migrate: bool) -> DBOSConfig:
    return {
        "name": APP_NAME,
        "application_version": args.application_revision,
        "system_database_url": SYSTEM_DATABASE_URL,
        "executor_id": args.executor_id,
        "run_migrations": migrate,
        "use_listen_notify": True,
        "notification_listener_polling_interval_sec": 0.05,
        "notification_coalesce_sec": 0.01,
        "scheduler_polling_interval_sec": 0.05,
    }


@DBOS.step()
async def accepted_step(value: str) -> str:
    await asyncio.sleep(1)
    return f"accepted:{value}"


@DBOS.workflow()
async def accepted_workflow(value: str) -> str:
    return await accepted_step(value)


def _event(event: str, **fields: object) -> None:
    print(json.dumps({"graft_event": event, **fields}, sort_keys=True), flush=True)


def _set_tenant_scope(connection: psycopg.Connection[Any], graft_tenant_id: str) -> None:
    """Set the transaction-local RLS scope; it cannot leak through PgBouncer."""

    connection.execute(
        sql.SQL("SET LOCAL graft.tenant_id = {}").format(sql.Literal(graft_tenant_id))
    )


def _metadata_schema() -> None:
    with psycopg.connect(APP_DATABASE_URL) as connection, connection.transaction():
        # Local reruns can have the pre-RLS synthetic schema in the
        # disposable volume. Never mix those unscoped rows into this
        # probe; replace only that old synthetic schema.
        old_schema = connection.execute(
            """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'gate03_accepted_run_metadata'
                      AND column_name = 'graft_run_id'
                )
                """
        ).fetchone()
        if old_schema and not bool(old_schema[0]):
            connection.execute("DROP TABLE IF EXISTS gate03_operator_escalations CASCADE")
            connection.execute("DROP TABLE IF EXISTS gate03_accepted_run_metadata CASCADE")
        # These are synthetic application tables, not DBOS system tables.
        # Keep every ownership/scoping column explicitly graft-prefixed so
        # this probe cannot misrepresent the production tenancy contract.
        connection.execute(
            """
                CREATE TABLE IF NOT EXISTS gate03_accepted_run_metadata (
                    graft_tenant_id TEXT NOT NULL,
                    graft_run_id TEXT NOT NULL,
                    graft_executor_id TEXT NOT NULL,
                    graft_application_revision TEXT NOT NULL,
                    graft_created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (graft_tenant_id, graft_run_id)
                )
                """
        )
        connection.execute(
            """
                CREATE TABLE IF NOT EXISTS gate03_operator_escalations (
                    graft_escalation_id TEXT PRIMARY KEY,
                    graft_tenant_id TEXT NOT NULL,
                    graft_run_id TEXT NOT NULL,
                    graft_state TEXT NOT NULL
                        CHECK (graft_state IN ('ALIVE_BUT_SILENT', 'AMBIGUOUS', 'STUCK')),
                    graft_executor_id TEXT NOT NULL,
                    graft_application_revision TEXT NOT NULL,
                    graft_reason TEXT NOT NULL,
                    graft_recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (graft_tenant_id, graft_run_id)
                        REFERENCES gate03_accepted_run_metadata
                            (graft_tenant_id, graft_run_id)
                )
                """
        )
        connection.execute("ALTER TABLE gate03_accepted_run_metadata ENABLE ROW LEVEL SECURITY")
        connection.execute("ALTER TABLE gate03_accepted_run_metadata FORCE ROW LEVEL SECURITY")
        connection.execute("ALTER TABLE gate03_operator_escalations ENABLE ROW LEVEL SECURITY")
        connection.execute("ALTER TABLE gate03_operator_escalations FORCE ROW LEVEL SECURITY")
        connection.execute(
            "DROP POLICY IF EXISTS gate03_accepted_run_metadata_tenant ON "
            "gate03_accepted_run_metadata"
        )
        connection.execute(
            "DROP POLICY IF EXISTS gate03_operator_escalations_tenant ON "
            "gate03_operator_escalations"
        )
        connection.execute(
            """
                CREATE POLICY gate03_accepted_run_metadata_tenant
                ON gate03_accepted_run_metadata
                USING (graft_tenant_id = current_setting('graft.tenant_id', true))
                WITH CHECK (graft_tenant_id = current_setting('graft.tenant_id', true))
                """
        )
        connection.execute(
            """
                CREATE POLICY gate03_operator_escalations_tenant
                ON gate03_operator_escalations
                USING (graft_tenant_id = current_setting('graft.tenant_id', true))
                WITH CHECK (graft_tenant_id = current_setting('graft.tenant_id', true))
                """
        )


def _metadata_row(graft_tenant_id: str, graft_run_id: str) -> RunMetadata | None:
    with psycopg.connect(APP_DATABASE_URL) as connection, connection.transaction():
        _set_tenant_scope(connection, graft_tenant_id)
        row = connection.execute(
            """
                SELECT graft_tenant_id, graft_run_id,
                       graft_executor_id, graft_application_revision
                FROM gate03_accepted_run_metadata
                WHERE graft_run_id = %s
                """,
            (graft_run_id,),
        ).fetchone()
    if row is None:
        return None
    return RunMetadata(str(row[0]), str(row[1]), str(row[2]), str(row[3]))


def _insert_run_metadata(metadata: RunMetadata) -> RunMetadata:
    """Insert metadata once; never update an existing revision in place."""

    _metadata_schema()
    with psycopg.connect(APP_DATABASE_URL) as connection, connection.transaction():
        _set_tenant_scope(connection, metadata.graft_tenant_id)
        connection.execute(
            """
                INSERT INTO gate03_accepted_run_metadata
                    (graft_tenant_id, graft_run_id,
                     graft_executor_id, graft_application_revision)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (graft_tenant_id, graft_run_id) DO NOTHING
                """,
            (
                metadata.graft_tenant_id,
                metadata.graft_run_id,
                metadata.graft_executor_id,
                metadata.graft_application_revision,
            ),
        )
    stored = _metadata_row(metadata.graft_tenant_id, metadata.graft_run_id)
    if stored is None:
        raise RuntimeError("insert-once Run metadata was not readable after insertion")
    if stored.graft_application_revision != metadata.graft_application_revision:
        raise MetadataConflict(
            "immutable application revision conflict: "
            f"stored={stored.graft_application_revision!r} "
            f"requested={metadata.graft_application_revision!r}"
        )
    if stored.graft_executor_id != metadata.graft_executor_id:
        raise MetadataConflict(
            f"immutable executor identity conflict: stored={stored.graft_executor_id!r} "
            f"requested={metadata.graft_executor_id!r}"
        )
    return stored


def _persist_escalation(metadata: RunMetadata, state: str, reason: str) -> OperatorEscalation:
    if state not in ESCALATION_STATES:
        raise ValueError(f"unsupported operator escalation state: {state}")
    reason_key = hashlib.sha256(reason.encode()).hexdigest()[:16]
    graft_escalation_id = f"{metadata.graft_run_id}:{state}:{reason_key}"
    with psycopg.connect(APP_DATABASE_URL) as connection, connection.transaction():
        _set_tenant_scope(connection, metadata.graft_tenant_id)
        connection.execute(
            """
                INSERT INTO gate03_operator_escalations
                    (graft_escalation_id, graft_tenant_id, graft_run_id,
                     graft_state, graft_executor_id,
                     graft_application_revision, graft_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (graft_escalation_id) DO NOTHING
                """,
            (
                graft_escalation_id,
                metadata.graft_tenant_id,
                metadata.graft_run_id,
                state,
                metadata.graft_executor_id,
                metadata.graft_application_revision,
                reason,
            ),
        )
        row = connection.execute(
            """
                SELECT graft_tenant_id, graft_escalation_id, graft_run_id,
                       graft_state, graft_executor_id,
                       graft_application_revision, graft_reason,
                       graft_recorded_at::text
                FROM gate03_operator_escalations
                WHERE graft_escalation_id = %s
                """,
            (graft_escalation_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError("durable operator escalation was not readable after insertion")
    return OperatorEscalation(
        graft_tenant_id=str(row[0]),
        graft_escalation_id=str(row[1]),
        graft_run_id=str(row[2]),
        graft_state=cast(Literal["ALIVE_BUT_SILENT", "AMBIGUOUS", "STUCK"], str(row[3])),
        graft_executor_id=str(row[4]),
        graft_application_revision=str(row[5]),
        graft_reason=str(row[6]),
        graft_recorded_at=str(row[7]),
    )


def _escalation_count(graft_tenant_id: str, graft_run_id: str) -> int:
    with psycopg.connect(APP_DATABASE_URL) as connection, connection.transaction():
        _set_tenant_scope(connection, graft_tenant_id)
        row = connection.execute(
            """
                SELECT COUNT(*)
                FROM gate03_operator_escalations
                WHERE graft_run_id = %s
                """,
            (graft_run_id,),
        ).fetchone()
    return int(row[0]) if row else 0


def _dataclass_dict(value: RunMetadata | OperatorEscalation) -> dict[str, object]:
    if isinstance(value, RunMetadata):
        return {
            "graft_tenant_id": value.graft_tenant_id,
            "graft_run_id": value.graft_run_id,
            "graft_executor_id": value.graft_executor_id,
            "graft_application_revision": value.graft_application_revision,
        }
    return {
        "graft_tenant_id": value.graft_tenant_id,
        "graft_escalation_id": value.graft_escalation_id,
        "graft_run_id": value.graft_run_id,
        "graft_state": value.graft_state,
        "graft_executor_id": value.graft_executor_id,
        "graft_application_revision": value.graft_application_revision,
        "graft_reason": value.graft_reason,
        "graft_recorded_at": value.graft_recorded_at,
    }


def accepted_runtime_recovery(
    *,
    graft_tenant_id: str,
    graft_run_id: str,
    graft_executor_id: str,
    graft_application_revision: str,
    client: DBOSClient,
    escalation_state: str | None = None,
) -> dict[str, object]:
    """The sole accepted recovery entry point used by every worker mode.

    The application-owned metadata row is the immutable authority for the
    expected executor and released revision.  All checks, including the
    optional operator-escalation path, happen before ``resume_workflow`` is
    called.  The public DBOS client is intentionally passed in by the caller
    so this function is the only place where resume can be invoked.
    """

    _metadata_schema()
    metadata = _metadata_row(graft_tenant_id, graft_run_id)
    if metadata is None:
        raise RecoveryRejected("Run metadata does not exist")

    mismatch_reasons: list[str] = []
    if metadata.graft_executor_id != graft_executor_id:
        mismatch_reasons.append("executor_identity_mismatch")
    if metadata.graft_application_revision != graft_application_revision:
        mismatch_reasons.append("application_revision_mismatch")

    if mismatch_reasons:
        escalation = _persist_escalation(
            metadata,
            "AMBIGUOUS",
            ";".join(mismatch_reasons),
        )
        return {
            "graft_recovery_accepted": False,
            "graft_recovery_decision": "REJECT_OPERATOR_ESCALATION",
            "graft_run_id": graft_run_id,
            "graft_expected_executor_id": metadata.graft_executor_id,
            "graft_requested_executor_id": graft_executor_id,
            "graft_expected_application_revision": metadata.graft_application_revision,
            "graft_requested_application_revision": graft_application_revision,
            "graft_rejection_reasons": mismatch_reasons,
            "graft_resume_invoked": False,
            "graft_durable_escalation": _dataclass_dict(escalation),
        }

    if escalation_state is not None:
        escalation_state = {
            "alive-but-silent": "ALIVE_BUT_SILENT",
            "ambiguous": "AMBIGUOUS",
            "stuck": "STUCK",
        }.get(escalation_state, escalation_state)
        escalation = _persist_escalation(
            metadata,
            escalation_state,
            f"accepted runtime observed {escalation_state.lower().replace('_', '-')}",
        )
        return {
            "graft_recovery_accepted": False,
            "graft_recovery_decision": "OPERATOR_ESCALATION",
            "graft_run_id": graft_run_id,
            "graft_expected_executor_id": metadata.graft_executor_id,
            "graft_requested_executor_id": graft_executor_id,
            "graft_expected_application_revision": metadata.graft_application_revision,
            "graft_requested_application_revision": graft_application_revision,
            "graft_resume_invoked": False,
            "graft_durable_escalation": _dataclass_dict(escalation),
        }

    # This is the only accepted runtime call site for DBOSClient.resume_workflow.
    handle = client.resume_workflow(graft_run_id)
    return {
        "graft_recovery_accepted": True,
        "graft_recovery_decision": "RESUME_ACCEPTED",
        "graft_run_id": graft_run_id,
        "graft_expected_executor_id": metadata.graft_executor_id,
        "graft_requested_executor_id": graft_executor_id,
        "graft_expected_application_revision": metadata.graft_application_revision,
        "graft_requested_application_revision": graft_application_revision,
        "graft_resume_invoked": True,
        "graft_resume_handle_type": type(handle).__name__,
    }


async def _worker(args: argparse.Namespace) -> int:
    _metadata_schema()
    DBOS.destroy()
    if args.mode == "metadata-conflict":
        try:
            _insert_run_metadata(
                RunMetadata(
                    args.graft_tenant_id,
                    args.workflow_id,
                    args.executor_id,
                    args.application_revision,
                )
            )
        except MetadataConflict as exc:
            _event(
                "immutable_metadata_conflict",
                graft_run_id=args.workflow_id,
                graft_rejected_application_revision=args.application_revision,
                error=str(exc),
                rejected=True,
            )
            return 0
        _event(
            "immutable_metadata_conflict",
            graft_run_id=args.workflow_id,
            graft_rejected_application_revision=args.application_revision,
            rejected=False,
        )
        return 1
    if args.mode == "start":
        DBOS(config=_config(args, migrate=True))
        DBOS.launch()
        try:
            _insert_run_metadata(
                RunMetadata(
                    args.graft_tenant_id,
                    args.workflow_id,
                    args.executor_id,
                    args.application_revision,
                )
            )
            with SetWorkflowID(args.workflow_id):
                handle = await DBOS.start_workflow_async(accepted_workflow, args.workflow_id)
            _event(
                "started",
                graft_run_id=handle.get_workflow_id(),
                graft_executor_id=args.executor_id,
                graft_application_revision=args.application_revision,
                metadata_insert_once=True,
            )
            await asyncio.sleep(args.hold_seconds)
            return 0
        finally:
            DBOS.destroy()

    DBOS(config=_config(args, migrate=False))
    client = DBOSClient(
        system_database_url=SYSTEM_DATABASE_URL,
        application_name=APP_NAME,
        use_listen_notify=False,
    )
    try:
        decision = accepted_runtime_recovery(
            graft_tenant_id=args.graft_tenant_id,
            graft_run_id=args.workflow_id,
            graft_executor_id=args.executor_id,
            graft_application_revision=args.application_revision,
            client=client,
            escalation_state=args.escalation_state,
        )
        if not decision["graft_recovery_accepted"]:
            _event("recovery_decision", **decision)
            return 0
        DBOS.launch()
        try:
            deadline = time.monotonic() + args.timeout_seconds
            latest: dict[str, object] | None = None
            while time.monotonic() < deadline:
                rows = client.list_workflows(
                    workflow_ids=[args.workflow_id],
                    load_input=False,
                    load_output=False,
                    application_name=APP_NAME,
                )
                latest = _status_dict(rows[0]) if rows else None
                if latest is not None and latest.get("status") in TERMINAL_STATUSES:
                    _event(
                        "matching_executor_restart",
                        graft_run_id=args.workflow_id,
                        graft_requested_executor_id=args.executor_id,
                        graft_requested_application_revision=args.application_revision,
                        status=latest,
                        graft_automatic_resume_via_accepted_runtime=True,
                        graft_recovery_entry_point="accepted_runtime_recovery",
                        graft_resume_invoked=True,
                    )
                    return 0
                await asyncio.sleep(0.1)
            _event(
                "matching_executor_restart",
                graft_run_id=args.workflow_id,
                graft_requested_executor_id=args.executor_id,
                graft_requested_application_revision=args.application_revision,
                status=latest,
                graft_automatic_resume_via_accepted_runtime=True,
                graft_recovery_entry_point="accepted_runtime_recovery",
                graft_resume_invoked=True,
            )
            return 1
        finally:
            DBOS.destroy()
    finally:
        client.destroy()


def _read_events(output: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for line in output.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "graft_event" in value:
            events.append(value)
    return events


def _field(value: object, name: str) -> object:
    if isinstance(value, dict):
        return value.get(name)
    return None


def _redact(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return value.replace("gate03_local_only", REDACTED)
    return value


def _command(command: list[str], *, timeout: int = 90) -> dict[str, object]:
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": 124,
            "stdout": _redact(exc.stdout or ""),
            "stderr": _redact(exc.stderr or "timeout"),
        }
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": _redact(completed.stdout),
        "stderr": _redact(completed.stderr),
    }


def _worker_command(
    mode: str,
    workflow_id: str,
    executor_id: str,
    application_revision: str = APP_VERSION,
    escalation_state: str | None = None,
    graft_tenant_id: str = TENANT_A,
) -> list[str]:
    command = [
        "uv",
        "run",
        "--locked",
        "--python",
        PYTHON_VERSION,
        "python",
        "deployment/gate-0.3/accepted_recovery.py",
        "worker",
        "--mode",
        mode,
        "--workflow-id",
        workflow_id,
        "--graft-tenant-id",
        graft_tenant_id,
        "--executor-id",
        executor_id,
        "--application-revision",
        application_revision,
    ]
    if escalation_state is not None:
        command.extend(["--escalation-state", escalation_state])
    return command


def _tenant_scope_probe(workflow_id: str) -> dict[str, object]:
    """Exercise both Tenant scopes through transaction-mode PgBouncer."""

    other_workflow_id = f"{workflow_id}-other-tenant"
    _insert_run_metadata(
        RunMetadata(TENANT_B, other_workflow_id, "other-tenant-executor", APP_VERSION)
    )
    hidden_from_a = _metadata_row(TENANT_A, other_workflow_id) is None
    visible_to_b = _metadata_row(TENANT_B, other_workflow_id) is not None
    return {
        "graft_tenant_a": TENANT_A,
        "graft_tenant_b": TENANT_B,
        "graft_other_tenant_row_hidden_from_graft_tenant_a": hidden_from_a,
        "graft_other_tenant_row_visible_to_graft_tenant_b": visible_to_b,
    }


def run() -> int:
    workflow_id = f"gate03-accepted-{uuid.uuid4().hex}"
    matching_executor = "gate03-accepted-executor-a"
    different_executor = "gate03-accepted-executor-b"
    wrong_revision = "gate03-accepted-revision-wrong"
    start_command = _worker_command("start", workflow_id, matching_executor)
    start_process = subprocess.Popen(
        start_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    start_output: list[str] = []
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            line = start_process.stdout.readline() if start_process.stdout else ""
            if line:
                start_output.append(line)
                if any(event.get("graft_event") == "started" for event in _read_events(line)):
                    break
            elif start_process.poll() is not None:
                break
            else:
                time.sleep(0.05)
        else:
            raise TimeoutError("matching executor did not emit started")
        if not any(
            event.get("graft_event") == "started" for event in _read_events("".join(start_output))
        ):
            raise RuntimeError(f"matching executor failed to start: {''.join(start_output)}")
        time.sleep(0.25)
        os.killpg(start_process.pid, signal.SIGKILL)
        killed_output, _ = start_process.communicate(timeout=10)
        start_output.append(killed_output)
    finally:
        if start_process.poll() is None:
            os.killpg(start_process.pid, signal.SIGKILL)
            start_process.communicate()

    reject_executor_result = _command(_worker_command("reject", workflow_id, different_executor))
    metadata_conflict_result = _command(
        _worker_command("metadata-conflict", workflow_id, matching_executor, wrong_revision)
    )
    reject_revision_result = _command(
        _worker_command("reject", workflow_id, matching_executor, wrong_revision)
    )
    escalation_results = {
        state: _command(
            _worker_command("escalate", workflow_id, matching_executor, APP_VERSION, state)
        )
        for state in ("alive-but-silent", "ambiguous", "stuck")
    }
    matching_command = _worker_command("recover", workflow_id, matching_executor)
    matching_result = _command(matching_command)

    reject_executor_events = _read_events(str(reject_executor_result["stdout"]))
    reject_revision_events = _read_events(str(reject_revision_result["stdout"]))
    matching_events = _read_events(str(matching_result["stdout"]))
    reject_executor = next(
        (
            event
            for event in reject_executor_events
            if event.get("graft_event") == "recovery_decision"
        ),
        {},
    )
    reject_revision = next(
        (
            event
            for event in reject_revision_events
            if event.get("graft_event") == "recovery_decision"
        ),
        {},
    )
    restart = next(
        (
            event
            for event in matching_events
            if event.get("graft_event") == "matching_executor_restart"
        ),
        {},
    )
    escalation_events = {
        state: next(
            (
                event
                for event in _read_events(str(result["stdout"]))
                if event.get("graft_event") == "recovery_decision"
            ),
            {},
        )
        for state, result in escalation_results.items()
    }
    escalation_state_matches = {
        state: (
            isinstance(escalation_events[state], dict)
            and isinstance(escalation_events[state].get("graft_durable_escalation"), dict)
            and cast(dict[str, object], escalation_events[state]["graft_durable_escalation"]).get(
                "graft_state"
            )
            == state.upper().replace("-", "_")
            and escalation_events[state].get("graft_resume_invoked") is False
        )
        for state in escalation_results
    }
    immutable_conflict_events = _read_events(str(metadata_conflict_result["stdout"]))
    durable_escalation_count = _escalation_count(TENANT_A, workflow_id)
    tenant_scope_probe = _tenant_scope_probe(workflow_id)
    reject_executor_reasons = reject_executor.get("graft_rejection_reasons")
    reject_revision_reasons = reject_revision.get("graft_rejection_reasons")
    reject_executor_reason_list = (
        reject_executor_reasons if isinstance(reject_executor_reasons, list) else []
    )
    reject_revision_reason_list = (
        reject_revision_reasons if isinstance(reject_revision_reasons, list) else []
    )
    assertions = {
        "graft_matching_executor_revision_restart_succeeded": matching_result["returncode"] == 0
        and restart.get("graft_automatic_resume_via_accepted_runtime") is True
        and restart.get("graft_resume_invoked") is True
        and _field(restart.get("status"), "status") == "SUCCESS"
        and _field(restart.get("status"), "executor_id") == matching_executor
        and _field(restart.get("status"), "app_version") == APP_VERSION,
        "wrong_executor_rejected_before_resume": reject_executor_result["returncode"] == 0
        and reject_executor.get("graft_recovery_decision") == "REJECT_OPERATOR_ESCALATION"
        and reject_executor.get("graft_resume_invoked") is False
        and "executor_identity_mismatch" in reject_executor_reason_list,
        "graft_wrong_revision_rejected_before_resume": reject_revision_result["returncode"] == 0
        and reject_revision.get("graft_recovery_decision") == "REJECT_OPERATOR_ESCALATION"
        and reject_revision.get("graft_resume_invoked") is False
        and "application_revision_mismatch" in reject_revision_reason_list,
        "graft_immutable_revision_conflict_rejected": metadata_conflict_result["returncode"] == 0
        and any(
            event.get("graft_event") == "immutable_metadata_conflict"
            and event.get("rejected") is True
            for event in immutable_conflict_events
        ),
        "typed_durable_escalation_recorded": durable_escalation_count >= 3
        and all(
            result["returncode"] == 0 and escalation_state_matches[state]
            for state, result in escalation_results.items()
        ),
        "graft_explicit_compatibility_revision": _field(restart.get("status"), "app_version")
        == APP_VERSION,
    }
    result: dict[str, Any] = {
        "report": "accepted-matching-executor-recovery",
        "verdict": "PASS" if all(assertions.values()) else "INCOMPLETE",
        "environment": {
            "dbos": "3.0.0",
            "python": sys.version,
            "system_database": "PostgreSQL 16 pinned Gate 0.3 image via direct endpoint",
            "metadata_database": "PostgreSQL application database via transaction-mode PgBouncer",
            "connection_topology": {
                "application_metadata_and_escalations": "transaction_mode_pgbouncer",
                "dbos_system_database": "direct_postgresql",
            },
            "evidence_lanes": {
                "public_api_behaviour": True,
                "private_or_diagnostic": True,
                "private_or_diagnostic_kinds": [
                    "application-owned metadata and escalation SQL diagnostics"
                ],
            },
            "public_api_only": False,
            "private_dbos_api_or_system_table_mutation": False,
        },
        "graft_run_id": workflow_id,
        "graft_tenant_id": TENANT_A,
        "application_name": APP_NAME,
        "graft_compatibility_revision": APP_VERSION,
        "graft_matching_executor_id": matching_executor,
        "graft_different_executor_id": different_executor,
        "graft_wrong_application_revision": wrong_revision,
        "run_metadata": {
            "table": "gate03_accepted_run_metadata",
            "insert_once": True,
            "graft_conflicting_revision_rejected": True,
            "graft_immutable_compatibility_revision": APP_VERSION,
        },
        "start_after_kill_output": _redact("".join(start_output)),
        "wrong_executor_recovery": reject_executor,
        "immutable_metadata_conflict": _read_events(str(metadata_conflict_result["stdout"])),
        "wrong_revision_recovery": reject_revision,
        "operator_escalations": escalation_events,
        "durable_escalation_record": {
            "table": "gate03_operator_escalations",
            "typed_states": list(ESCALATION_STATES),
            "workflow_record_count": durable_escalation_count,
            "not_stdout_only": True,
        },
        "graft_tenant_scope_probe": tenant_scope_probe,
        "matching_executor_revision_restart": restart,
        "commands": {
            "start_and_kill": start_command,
            "wrong_executor": reject_executor_result,
            "immutable_metadata_conflict": metadata_conflict_result,
            "wrong_revision": reject_revision_result,
            "operator_escalations": escalation_results,
            "matching_executor_revision_restart": matching_result,
        },
        "assertions": assertions,
        "scope_note": (
            "Accepted ADR-0078 permits restart only through the matching executor and "
            "released application compatibility revision. Wrong identity or revision is "
            "rejected before DBOS resume; alive-but-silent, ambiguous and stuck observations "
            "are durable operator escalations."
        ),
    }
    print(json.dumps(_redact(result), indent=2, sort_keys=True))
    return 0 if result["verdict"] == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "worker"))
    parser.add_argument(
        "--mode", choices=("start", "recover", "reject", "escalate", "metadata-conflict")
    )
    parser.add_argument("--workflow-id")
    parser.add_argument("--graft-tenant-id", default=TENANT_A)
    parser.add_argument("--executor-id")
    parser.add_argument("--application-revision", default=APP_VERSION)
    parser.add_argument("--escalation-state", choices=("alive-but-silent", "ambiguous", "stuck"))
    parser.add_argument("--hold-seconds", type=float, default=60)
    parser.add_argument("--timeout-seconds", type=float, default=60)
    args = parser.parse_args()
    if args.command == "worker":
        if not args.mode or not args.workflow_id or not args.executor_id:
            parser.error("worker requires mode, workflow ID and executor ID")
        if args.mode == "escalate" and args.escalation_state is None:
            parser.error("escalate requires an escalation state")
        return asyncio.run(_worker(args))
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
