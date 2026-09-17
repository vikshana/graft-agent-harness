---
id: ADR-0048
title: A thin runtime seam isolates the durable-execution engine
status: accepted
date: 2026-09-12
deciders: [ ]
category: agent
tags: [ agent, orchestration, durability ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ADR-0037, ADR-0039, ADR-0041 ]
design: ../../design/durable-execution.md
legacy_id: D48
---

# ADR-0048 — A thin runtime seam isolates the durable-execution engine

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D48`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

ADR-0037 embeds DBOS directly in the worker process, as a direct dependency rather than behind an abstraction port.
Because of that, the team needed to assess reversibility — how costly a future migration to a different engine (e.g.
Temporal) would actually be — and decide whether to build a full abstraction layer (the previously-considered
`RunController` port), a thinner seam, or nothing at all; and to identify the real trigger for revisiting the engine
choice (throughput versus topology).

## 2. Decision

**Reversibility assessed; a thin `runtime` seam replaces the rejected
`RunController` port — and throughput is the wrong trigger to watch.**
Migrating to Temporal later would be **moderate, bounded and mostly mechanical**: ADR-0041's step granularity maps 1:1
onto Temporal's workflow/child-workflow/activity model (discharging the briefing's central
"the irreversible part is graph decomposition" worry), signals/timers/ dedupe/deadlines are ≈1:1, and ADR-0038's reaper
would simply be **deleted**. Only two areas are genuine rework: **ADR-0044's per-partition queue flow control**
(Temporal has no comparable queueing/flow-control abstraction) and **ADR-0040's `fork_workflow` eval loop**. On scale
specifically: our workload (tens of concurrent runs, ~1 step/sec/run) sits **2–3 orders of magnitude** below DBOS's >40K
steps/sec single-Postgres benchmark; the binding constraints will be LLM/GPU capacity, customer-infrastructure tool
limits, and **Postgres connection count**
(pooler, not engine) — none of which Temporal improves, and raw throughput has a cheaper escape via sharding system
databases on R3's tenant key. The realistic revisit trigger is **topology (multi-cloud active-active, X5)**, not scale.
**DBOSify** (drop-in Temporal-SDK-compatible layer on Postgres)
was **considered and rejected** as a hedge: writing to the Temporal API surface would permanently forfeit the
partitioned queues, `fork`,
`deduplication_id` and runtime-mutable schedules this design depends on, to insure an unlikely event it does not
actually cover. **Instead: a single internal `runtime` module** (`enqueue_run`/`await_human`/`signal`/
`sleep_until`/`cancel`/`resume`/`fork`/`list_*`) is the sole importer of
`dbos`, which is worthwhile independently as the natural chokepoint for ADR-0015 audit emission, ADR-0029 event
publication, R3 scoping and ADR-0017 ceiling checks. It explicitly does **not** make the engine config-swappable.

## 3. Considered options

| Option                                                                      | Verdict     | Why                                                                                                                                                                                                            |
|-----------------------------------------------------------------------------|-------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A full abstraction port (`RunController`) making the engine swappable       | ❌ Rejected | Not worth the design cost — migration to Temporal, if it ever happens, is assessed as moderate/bounded/mostly mechanical without one.                                                                          |
| `DBOSify` — a drop-in Temporal-SDK-compatible layer on Postgres, as a hedge | ❌ Rejected | Writing to the Temporal API surface would permanently forfeit DBOS's partitioned queues, `fork`, `deduplication_id` and runtime-mutable schedules, to insure against an unlikely event it doesn't even cover.  |
| A single internal `runtime` module as the sole importer of `dbos`           | ✅ Chosen   | Worthwhile independently as the natural chokepoint for ADR-0015 audit emission, ADR-0029 event publication, tenant scoping and ADR-0017 ceiling checks — without claiming to make the engine config-swappable. |

## 4. Consequences

- **Positive —** migrating to Temporal later, if ever needed, is moderate and mostly mechanical: ADR-0041's step
  granularity maps ~1:1 onto Temporal's workflow/child-workflow/activity model, signals/timers/ dedupe/deadlines are ≈1:
  1, and ADR-0038's reaper would simply be deleted.
- **Negative / accepted trade —** two areas would require genuine rework if migrating: ADR-0044's per-partition queue
  flow control (no comparable Temporal abstraction) and ADR-0040's `fork_workflow` eval loop.
- **Follow-on work —** the `runtime` module explicitly does **not** make the engine config-swappable; it exists as a
  chokepoint for audit, event publication, tenant scoping and budget-ceiling concerns, not as an abstraction layer.
- **Revisit trigger —** **topology** (multi-cloud active-active, risk X5 — resolved by ADR-0049), not scale: current
  workload sits 2–3 orders of magnitude below DBOS's published throughput ceiling.

## 5. Verification

- Connection behaviour under concurrency — verified 2026-09-13 against a live scratch Postgres 16, `dbos==2.31.1` (spike
  S2, experiment E5). Result: DBOS held 8 backend connections at idle (two bounded pools: system + app) and 25 for 50
  concurrently in-flight workflows (~0.5 connections per in-flight workflow) — confirming connection count is bounded by
  DBOS's configured pool sizes, not 1:1 with workflow concurrency, and giving a concrete number to feed into capacity
  planning.
- pgbouncer transaction-mode compatibility — verified 2026-09-13 (spike S2, experiment E4). Result: DBOS's own
  workflows, including a `send`/`recv` round trip, completed correctly through a transaction-mode pgbouncer with both
  `use_listen_notify=True` (default, session-scoped `LISTEN`) and `use_listen_notify=False` (documented polling
  fallback). This was a single-process smoke test, not a multi-worker production-scale stress test. Full experiment
  log: [`../../design/durable-execution.md`](../../design/durable-execution.md) section 4.5.
