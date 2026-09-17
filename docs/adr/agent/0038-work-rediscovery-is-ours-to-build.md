---
id: ADR-0038
title: Work rediscovery is ours to build
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
legacy_id: D38
---

# ADR-0038 — Work rediscovery is ours to build

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D38`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

ADR-0037 chose DBOS Transact and explicitly excluded DBOS Conductor, the paid companion service that would otherwise
provide distributed recovery — automatically reassigning a dead pod's workflows to a live worker. Without Conductor,
work rediscovery (resuming a workflow whose worker pod died) has to be built.

## 2. Decision

**Work rediscovery is ours to build — ~150 lines, not a durable engine.**
Because Conductor is excluded, distributed recovery is **`executor_id`-pinned**: a dead pod's workflows recover only
when a pod with that same executor ID restarts. Design: workers are a **StatefulSet**
with executor IDs carrying pod ordinal **and deploy colour** (`blue-0`,
`green-0`, per ADR-0046); each worker heartbeats
`(executor_id, app_version, last_seen_at)` to a table we own; a **version-aware reaper** (itself a scheduled DBOS
workflow) resumes
`PENDING` workflows whose executor's heartbeat is stale, onto a live worker **of the matching version**. All runs are
**enqueued, never started in-process**, confining the exposure window to genuinely in-flight runs.

## 3. Considered options

| Option                                                                                       | Verdict     | Why                                                                                                                                          |
|----------------------------------------------------------------------------------------------|-------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| Use DBOS Conductor for distributed recovery                                                  | ❌ Rejected | Already excluded by ADR-0037's product constraint: no paid plans, no separate orchestration service.                                         |
| Build our own `executor_id`-pinned work rediscovery (heartbeat table + version-aware reaper) | ✅ Chosen   | A small (~150 line), self-contained mechanism rather than a durable engine; recovery is confined to a dead pod's own executor ID restarting. |

## 4. Consequences

- **Positive —** small, contained implementation; does not require a separate orchestration service or paid plan.
- **Negative / accepted trade —** recovery is `executor_id`-pinned — a workflow only recovers when a pod with the *same*
  executor ID restarts, not onto any available worker; the reaper must also match deploy colour (ADR-0046), or a
  recovered run could land on the wrong version.
- **Follow-on work —** workers ship as a StatefulSet; each worker heartbeats
  `(executor_id, app_version, last_seen_at)`; all runs are enqueued, never started in-process, to bound the exposure
  window to genuinely in-flight runs.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/durable-execution.md`](../../design/durable-execution.md).
