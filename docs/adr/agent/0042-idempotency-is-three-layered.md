---
id: ADR-0042
title: Idempotency is three-layered
status: accepted
date: 2026-09-12
deciders: [ ]
category: agent
tags: [ agent, orchestration, durability ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/durable-execution.md
legacy_id: D42
---

# ADR-0042 — Idempotency is three-layered

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D42`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

Durable runs can retry, reconnect, and be replayed via fork (ADR-0040's
`fork_workflow`). Run creation, trigger dedupe (alert storms re-firing), and write side effects each have different
retry/replay semantics, and each needed its own idempotency guarantee — otherwise a replay could re-file a support
ticket or re-open a pull request.

## 2. Decision

**Idempotency is three-layered:** `workflow_id` (caller-supplied key) for **run creation**; `deduplication_id` on the
queue for **trigger dedupe**
(alert storms re-firing); `(graft_run_id, step_id, idempotency_key)` for **write side effects**, forwarded to the Tool
Gateway and to upstream idempotency facilities where they exist. Must survive retry, reconnect **and
replay-after-fork**. **Forked/eval runs are structurally read-only** — denied write tool classes by the same
capability-token mechanism as ADR-0013 — because `fork_workflow` deliberately re-executes and would otherwise re-file a
Jira ticket or re-open a PR when replaying an incident.

## 3. Considered options

| Option                                                                                              | Verdict     | Why                                                                                                                                                                                             |
|-----------------------------------------------------------------------------------------------------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A single global idempotency key for the whole run                                                   | ❌ Rejected | Run creation, trigger dedupe, and write side effects have different retry/replay semantics — one key could not correctly dedupe alert-storm re-firing separately from a step-level write retry. |
| Three-layered keys: `workflow_id` / `deduplication_id` / `(graft_run_id, step_id, idempotency_key)` | ✅ Chosen   | Each layer maps to a distinct source of duplication (caller retry, alert storm re-fire, step retry/replay).                                                                                     |
| Allow forked/eval runs (ADR-0040) to perform writes                                                 | ❌ Rejected | `fork_workflow` deliberately re-executes; allowing writes would re-file a ticket or re-open a PR when replaying an incident.                                                                    |

## 4. Consequences

- **Positive —** idempotency survives retry, reconnect, and replay-after-fork across all three layers.
- **Negative / accepted trade —** forked/eval runs are structurally read-only — denied write tool classes by the same
  capability-token mechanism as ADR-0013 — so replay-for-eval cannot exercise write-path tools even when that would
  otherwise be useful for testing.
- **Follow-on work —** the write-layer key is forwarded to the Tool Gateway and to upstream idempotency facilities where
  they exist.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/durable-execution.md`](../../design/durable-execution.md).
