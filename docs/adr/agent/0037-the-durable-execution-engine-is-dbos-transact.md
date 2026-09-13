---
id: ADR-0037
title: The durable-execution engine is DBOS Transact
status: accepted
date: 2026-09-12
deciders: []
category: agent
tags: [agent, orchestration, durability]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/durable-execution.md
legacy_id: D37
---

# ADR-0037 — The durable-execution engine is DBOS Transact

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D37`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Durable-execution engine is DBOS Transact** — an **MIT-licensed library embedded in the worker process**, backed by the Postgres we already run. **Temporal rejected** and **DBOS Conductor rejected** by an explicit product constraint (2026-09-12): no paid plans, no separate orchestration service. Bare-worker + LangGraph-checkpoints (briefing option (c)) remains rejected as failing the 30-minute / multi-hour-HITL requirements. Critically, this is **not** the briefing's feared "two weeks building a durable-execution engine": every capability in `04`'s section 3 table is native to DBOS **except work rediscovery** (see ADR-0038). Note the determinism constraint is **not** a Temporal-specific cost — DBOS imposes the identical rule (workflow functions deterministic, all I/O in steps), already largely satisfied by ADR-0003.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
