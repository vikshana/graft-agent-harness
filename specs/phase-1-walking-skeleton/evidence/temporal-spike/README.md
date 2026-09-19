# Temporal comparison spike evidence

> **Date:** 2026-09-19

This is disposable, synthetic-only comparison evidence. It is not a product
implementation, does not change the selected DBOS engine, and does not claim a
production deployment or customer-system access. Credentials in the Compose
file are local placeholders only and are not repeated in this evidence.

## Exact environment and commands

| Item | Version / command |
|---|---|
| Temporal Server | `temporalio/auto-setup:1.29.1@sha256:5b3502a3b685f9eff1b925af90c57c9e3dbeccbef367cc28a2a9712c63379312` |
| PostgreSQL | `postgres:16.8-alpine@sha256:3b057e1c2c6dfee60a30950096f3fab33be141dbb0fdd7af3d477083de94166c` |
| Python SDK | `temporalio==1.20.0` |
| Start | `docker compose -f deployment/temporal-spike/docker-compose.yml up -d --wait` |
| Run | `uv run --group temporal-spike python deployment/temporal-spike/run_spike.py --evidence-dir specs/phase-1-walking-skeleton/evidence/temporal-spike` |
| Cleanup | `docker compose -f deployment/temporal-spike/docker-compose.yml down -v --remove-orphans` |

The exact runner invocation and the Compose commands are retained in
`commands.json`. Raw worker logs and the server-returned workflow histories are
retained beside this file. They contain synthetic IDs only; no customer
credentials or customer payloads were used.

## Result classification

`result.json` classifies the run as `PASS_WITH_LIMITATIONS`.

| Observation | Result |
|---|---|
| Hard worker death, retry, timeout and heartbeat | `PASS`: first worker exited `137` after sending heartbeat 3. The replacement saw heartbeat detail from attempt 1, and the history recorded `TIMEOUT_TYPE_HEARTBEAT` as the retry failure before attempt 2 completed. The first dead worker also caused a workflow-task schedule-to-start timeout while its sticky queue was unavailable. |
| Post-effect worker death | `PASS_WITH_LIMITATIONS`: the first worker exited `137` after the HTTP effect, and the replacement retried it. The receiver recorded 2 raw calls for 1 stable key and applied 1 keyed logical effect. This is at-least-once execution, not exactly-once execution. |
| Compatibility mechanism | `PASS`: `workflow.patched("graft-temporal-spike-compat-v1")` was supported by the selected local server/SDK, recorded a `core_patch` marker, returned the new path, and replayed successfully through the SDK `Replayer`. |

Temporal does **not** fence external effects. The keyed synthetic receiver,
not Temporal, collapsed the duplicate logical effect. A dead or merely silent
worker can still result in an external effect being delivered more than once.

## Not covered

This spike does not cover DBOS step trajectories or `list_workflow_steps`,
`fork_workflow` evaluation replay, partition-key queue flow control and ceiling
enforcement, the DBOS PostgreSQL system-database/transaction-mode pooler
topology, or DBOS executor ownership, reaper selection and released
compatibility-revision policy. It is not a full engine migration assessment and
does not switch engines.
