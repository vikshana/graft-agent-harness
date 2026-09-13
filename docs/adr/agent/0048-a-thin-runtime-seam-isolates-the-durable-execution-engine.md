---
id: ADR-0048
title: A thin runtime seam isolates the durable-execution engine
status: accepted
date: 2026-09-12
deciders: []
category: agent
tags: [agent, orchestration, durability]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: [ADR-0037, ADR-0039, ADR-0041]
design: ../../design/durable-execution.md
legacy_id: D48
---

# ADR-0048 — A thin runtime seam isolates the durable-execution engine

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D48`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Reversibility assessed; a thin `runtime` seam replaces the rejected `RunController` port — and throughput is the wrong trigger to watch.** Migrating to Temporal later would be **moderate, bounded and mostly mechanical**: ADR-0041's step granularity maps 1:1 onto Temporal's workflow/child-workflow/activity model (discharging the briefing's central "the irreversible part is graph decomposition" worry), signals/timers/dedupe/deadlines are ≈1:1, and ADR-0038's reaper would simply be **deleted**. Only two areas are genuine rework: **ADR-0044's per-partition queue flow control** (Temporal has no comparable queueing/flow-control abstraction) and **ADR-0040's `fork_workflow` eval loop**. On scale specifically: our workload (tens of concurrent runs, ~1 step/sec/run) sits **2–3 orders of magnitude** below DBOS's >40K steps/sec single-Postgres benchmark; the binding constraints will be LLM/GPU capacity, customer-infrastructure tool limits, and **Postgres connection count** (pooler, not engine) — none of which Temporal improves, and raw throughput has a cheaper escape via sharding system databases on R3's tenant key. The realistic revisit trigger is **topology (multi-cloud active-active, X5)**, not scale. **DBOSify** (drop-in Temporal-SDK-compatible layer on Postgres) was **considered and rejected** as a hedge: writing to the Temporal API surface would permanently forfeit the partitioned queues, `fork`, `deduplication_id` and runtime-mutable schedules this design depends on, to insure an unlikely event it does not actually cover. **Instead: a single internal `runtime` module** (`enqueue_run`/`await_human`/`signal`/`sleep_until`/`cancel`/`resume`/`fork`/`list_*`) is the sole importer of `dbos`, which is worthwhile independently as the natural chokepoint for ADR-0015 audit emission, ADR-0029 event publication, R3 scoping and ADR-0017 ceiling checks. It explicitly does **not** make the engine config-swappable.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
