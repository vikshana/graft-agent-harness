"""Small Temporal worker used only by the disposable comparison spike."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import urllib.request
from datetime import timedelta
from typing import Any

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.worker import Worker

TASK_QUEUE = "graft-temporal-spike"
PATCH_ID = "graft-temporal-spike-compat-v1"
TEMPORAL_ADDRESS = os.environ.get("TEMPORAL_ADDRESS", "127.0.0.1:17233")


def _json_request(url: str, payload: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))


@activity.defn(name="graft-temporal-spike-activity")
async def spike_activity(scenario: str) -> dict[str, Any]:
    """Perform one retryable observation or one synthetic external effect."""

    info = activity.info()
    heartbeat_details = [detail for detail in info.heartbeat_details]

    if scenario == "heartbeat_death":
        if info.attempt == 1 and os.environ.get("SPIKE_CRASH_FIRST") == "1":
            for heartbeat_index in range(1, 4):
                activity.heartbeat(
                    {
                        "synthetic": True,
                        "attempt": info.attempt,
                        "heartbeat_index": heartbeat_index,
                    }
                )
                await asyncio.sleep(0.15)
            print("hard worker death after heartbeat 3", flush=True)
            os._exit(137)

        activity.heartbeat(
            {
                "synthetic": True,
                "attempt": info.attempt,
                "heartbeat_index": 4,
                "recovered": True,
            }
        )
        return {
            "scenario": scenario,
            "attempt": info.attempt,
            "heartbeat_details_seen_on_retry": heartbeat_details,
        }

    if scenario == "keyed_effect":
        effect_url = os.environ["SPIKE_EFFECT_URL"]
        effect_key = "graft-temporal-spike-run-effect-001"
        receiver_result = _json_request(
            effect_url,
            {"effect_key": effect_key, "run_id": "graft-temporal-spike-run-001"},
        )
        if info.attempt == 1 and os.environ.get("SPIKE_CRASH_FIRST") == "1":
            print("hard worker death after synthetic external effect", flush=True)
            os._exit(137)
        return {
            "scenario": scenario,
            "attempt": info.attempt,
            "receiver": receiver_result,
        }

    raise ValueError(f"unknown spike scenario: {scenario}")


@workflow.defn(name="graft-temporal-spike-recovery")
class RecoveryWorkflow:
    @workflow.run
    async def run(self, scenario: str) -> dict[str, Any]:
        heartbeat_timeout = timedelta(seconds=0.75) if scenario == "heartbeat_death" else None
        return await workflow.execute_activity(
            spike_activity,
            scenario,
            start_to_close_timeout=timedelta(seconds=3),
            heartbeat_timeout=heartbeat_timeout,
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=0.2),
                backoff_coefficient=1,
            ),
        )


@workflow.defn(name="graft-temporal-spike-compatibility")
class CompatibilityWorkflow:
    @workflow.run
    async def run(self) -> str:
        if workflow.patched(PATCH_ID):
            return "new-compatible-path"
        return "legacy-path"


async def run_worker() -> None:
    client = await Client.connect(TEMPORAL_ADDRESS, namespace="default")
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[RecoveryWorkflow, CompatibilityWorkflow],
        activities=[spike_activity],
        identity=os.environ.get("SPIKE_WORKER_ID", "temporal-spike-worker"),
    ):
        print(
            json.dumps(
                {
                    "worker": "ready",
                    "identity": os.environ.get("SPIKE_WORKER_ID", "temporal-spike-worker"),
                    "task_queue": TASK_QUEUE,
                    "crash_first": os.environ.get("SPIKE_CRASH_FIRST") == "1",
                }
            ),
            flush=True,
        )
        await asyncio.Event().wait()


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] != "worker":
        raise SystemExit("usage: temporal_spike.py worker")
    asyncio.run(run_worker())
