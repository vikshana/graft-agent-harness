#!/usr/bin/env python3
"""One independently started DBOS cohort for the Gate 0.3 Test 2 matrix."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from typing import TypeAlias

from dbos import DBOS, DBOSClient, DBOSConfig, SetEnqueueOptions, SetWorkflowID

SYSTEM_DATABASE_URL = os.environ.get(
    "G03_SYSTEM_DATABASE_URL", "postgresql://gate03@localhost:55433/gate03_system"
)
QUEUE_NAME = "gate03-matrix-dormant"
ACTIVE_STATUSES = ("ENQUEUED", "DELAYED", "PENDING")
StatusRecord: TypeAlias = dict[str, object] | None


@DBOS.step()
async def matrix_step(value: str) -> str:
    return f"complete:{value}"


@DBOS.step()
async def slow_matrix_step(value: str, sleep_seconds: float) -> str:
    await asyncio.sleep(sleep_seconds)
    return f"complete:{value}"


@DBOS.workflow()
async def matrix_workflow(value: str) -> str:
    return await matrix_step(value)


@DBOS.workflow()
async def pending_matrix_workflow(value: str, sleep_seconds: float) -> str:
    return await slow_matrix_step(value, sleep_seconds)


def _status_dict(status: object) -> StatusRecord:
    if status is None:
        return None
    fields = (
        "workflow_id",
        "status",
        "name",
        "executor_id",
        "app_version",
        "application_version",
        "application_name",
        "queue_name",
    )
    return {field: getattr(status, field, None) for field in fields}


def _status_is(status: StatusRecord, expected: str) -> bool:
    return status is not None and status["status"] == expected


def _status_is_terminal(status: StatusRecord) -> bool:
    return status is not None and status["status"] not in ACTIVE_STATUSES


async def _statuses(workflow_ids: list[str]) -> dict[str, StatusRecord]:
    return {
        workflow_id: _status_dict(await DBOS.get_workflow_status_async(workflow_id))
        for workflow_id in workflow_ids
    }


def _config(args: argparse.Namespace) -> DBOSConfig:
    return {
        "name": args.application_name,
        "application_version": args.application_version,
        "system_database_url": SYSTEM_DATABASE_URL,
        "executor_id": args.executor_id,
        "run_migrations": args.mode == "seed",
        "use_listen_notify": True,
        "notification_listener_polling_interval_sec": 0.05,
        "notification_coalesce_sec": 0.01,
        "scheduler_polling_interval_sec": 0.05,
        "max_executor_threads": 4,
    }


async def _seed(args: argparse.Namespace) -> None:
    queue = await DBOS.register_queue_async(
        QUEUE_NAME,
        worker_concurrency=0,
        polling_interval_sec=0.05,
        on_conflict="always_update",
    )
    del queue
    prefix = args.run_prefix
    enqueued_id = f"{prefix}-enqueued"
    delayed_id = f"{prefix}-delayed"
    pending_id = f"{prefix}-pending"
    with SetWorkflowID(enqueued_id):
        enqueued_handle = await DBOS.enqueue_workflow_async(
            QUEUE_NAME, matrix_workflow, enqueued_id
        )
    with SetWorkflowID(delayed_id), SetEnqueueOptions(delay_seconds=300):
        delayed_handle = await DBOS.enqueue_workflow_async(QUEUE_NAME, matrix_workflow, delayed_id)
    with SetWorkflowID(pending_id):
        pending_handle = await DBOS.start_workflow_async(
            pending_matrix_workflow, pending_id, args.step_sleep_seconds
        )
    workflow_ids = [
        enqueued_handle.get_workflow_id(),
        delayed_handle.get_workflow_id(),
        pending_handle.get_workflow_id(),
    ]
    deadline = time.monotonic() + 20
    snapshots: list[dict[str, StatusRecord]] = []
    while time.monotonic() < deadline:
        current = await _statuses(workflow_ids)
        snapshots.append(current)
        if (
            _status_is(current[enqueued_id], "ENQUEUED")
            and _status_is(current[delayed_id], "DELAYED")
            and _status_is(current[pending_id], "PENDING")
        ):
            print(
                json.dumps(
                    {
                        "event": "seeded",
                        "workflow_ids": workflow_ids,
                        "statuses": current,
                        "snapshots": snapshots[-3:],
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            while True:
                await asyncio.sleep(3600)
        await asyncio.sleep(0.05)
    raise RuntimeError(f"seed statuses did not reach the required matrix: {snapshots[-1]}")


async def _observe(args: argparse.Namespace) -> None:
    workflow_ids = args.workflow_ids.split(",")
    before = await _statuses(workflow_ids)
    client = DBOSClient(
        system_database_url=SYSTEM_DATABASE_URL,
        application_name=args.application_name,
    )
    try:
        listed = await client.list_workflows_async(
            workflow_ids=workflow_ids,
            load_input=False,
            load_output=False,
        )
    finally:
        client.destroy()
    after = await _statuses(workflow_ids)
    print(
        json.dumps(
            {
                "event": "observed",
                "cohort": args.application_version,
                "target_executor_id": args.target_executor_id,
                "public_observation": {
                    "api": "DBOSClient.list_workflows",
                    "listed_count": len(listed),
                    "cross_executor_recovery_attempted": False,
                    "note": (
                        "The public client can list and resume by workflow ID, but it "
                        "cannot condition resume on an expected executor or version."
                    ),
                },
                "before": before,
                "after": after,
            },
            sort_keys=True,
        ),
        flush=True,
    )


async def _recover_and_drain(args: argparse.Namespace) -> None:
    queue = await DBOS.register_queue_async(
        QUEUE_NAME,
        worker_concurrency=1,
        polling_interval_sec=0.05,
        on_conflict="always_update",
    )
    del queue
    workflow_ids = args.workflow_ids.split(",")
    client = DBOSClient(
        system_database_url=SYSTEM_DATABASE_URL,
        application_name=args.application_name,
    )
    await client.resume_workflows_async(workflow_ids)
    client.destroy()
    delayed_ids = [workflow_id for workflow_id in workflow_ids if workflow_id.endswith("-delayed")]
    for workflow_id in delayed_ids:
        await DBOS.set_workflow_delay_async(workflow_id, delay_seconds=0)
    deadline = time.monotonic() + args.drain_timeout_seconds
    snapshots: list[dict[str, StatusRecord]] = []
    while time.monotonic() < deadline:
        current = await _statuses(workflow_ids)
        snapshots.append(current)
        if all(_status_is_terminal(status) for status in current.values()):
            print(
                json.dumps(
                    {
                        "event": "drained",
                        "cohort": args.application_version,
                        "workflow_ids": workflow_ids,
                        "statuses": current,
                        "initial_snapshots": snapshots[:3],
                        "public_resume_api": "DBOSClient.resume_workflows",
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            return
        await asyncio.sleep(0.1)
    raise RuntimeError(f"cohort did not drain: {snapshots[-1]}")


async def _run(args: argparse.Namespace) -> None:
    DBOS.destroy()
    DBOS(config=_config(args))
    DBOS.launch()
    try:
        if args.mode == "seed":
            await _seed(args)
        elif args.mode == "observe":
            await _observe(args)
        elif args.mode == "recover":
            await _recover_and_drain(args)
        else:
            raise ValueError(f"unsupported mode: {args.mode}")
    finally:
        if args.mode != "seed":
            DBOS.destroy()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("seed", "observe", "recover"))
    parser.add_argument("--application-name", default="gate-0-3-recovery-matrix")
    parser.add_argument("--application-version", required=True)
    parser.add_argument("--executor-id", required=True)
    parser.add_argument("--run-prefix", default="forward")
    parser.add_argument("--workflow-ids", default="")
    parser.add_argument("--target-executor-id", default="")
    parser.add_argument("--step-sleep-seconds", type=float, default=30)
    parser.add_argument("--drain-timeout-seconds", type=float, default=60)
    args = parser.parse_args()
    if args.mode == "observe" and (not args.workflow_ids or not args.target_executor_id):
        parser.error("observe requires --workflow-ids and --target-executor-id")
    if args.mode == "recover" and not args.workflow_ids:
        parser.error("recover requires --workflow-ids")
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
