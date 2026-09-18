# Implementation Notes: Phase 1 API-first walking skeleton

> **Date:** 2026-09-17

---

## Summary

Added a runnable, dependency-light API contract/provider core for the Phase 1 walking skeleton. It models private read-only Runs, ordered replayable events, idempotent webhook creation, cancellation boundaries, capability-token validation, curated Tool Gateway calls, and a WSGI HTTP adapter while leaving production DBOS, PostgreSQL, MCP, telemetry, and surface transport integrations behind explicit seams.

## Deviations from the Plan

The plan was auto-generated because no `PLAN.md` existed and was not reviewed by a human. The first implementation deliberately uses an in-memory repository and deterministic model double because the repository has no application package or dependency configuration yet.

## Judgment Calls

- Chose JSON/OpenAPI plus Python dataclasses rather than a framework-specific schema library, so contract tests run on a clean Python installation and the semantic contract stays independent of Grafana or Slack.
- Chose HMAC capability tokens for the local security seam. Production must replace the signer with the approved capability-token authority while retaining the same validation claims and denial behaviour.

## Sanity Checks

| Check | Result | Notes |
|-------|--------|-------|
| `python3 -m unittest discover -s tests -v` | pass | 10 tests passed. |
| `python3 -m compileall -q harness tests` | pass | Python sources compile successfully. |
| Contract JSON parsing | pass | OpenAPI and event schema parse with `json.tool`. |
| `python3 scripts/check_step_pointer_rule.py harness` | pass | 6 Python files checked, 0 errors. |
| `python3 scripts/check_docs.py` | pre-existing failure | Reports dead link `docs/design/observability-pipeline.md` → `../../deployment/otel-collector/config.yaml`; unrelated to this implementation. |

## Out of Scope Observations

- Production DBOS recovery, PostgreSQL RLS execution, streamable-HTTP MCP, OTel Collector routing, Langfuse outage tests, and Grafana Live transport cannot be proven without the infrastructure and dependency decisions called out by the spec.

## Remaining Work

AC 6, AC 8, AC 12, AC 15, AC 17, AC 19, and AC 20 remain infrastructure/review work. AC 1–5, AC 9–11, and the local portions of AC 13–14 are covered by the new artifacts and tests. The migration and protocol seams are included so the remaining tests can be added without changing the public contract.



