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
relates_to: [ADR-0050, ADR-0060]
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

- Confirmed by **spike S1** (2026-09-13) — the LangGraph/DBOS integration boundary. See the Verification sections of [ADR-0039](0039-the-run-is-the-durable-workflow.md), [ADR-0040](0040-langgraph-is-compiled-with-no-checkpointer.md) and [ADR-0041](0041-step-granularity-is-one-llm-call-or-one-tool-call.md).
- Confirmed by **spike S2** (2026-09-13, experiments E1/E2/E6) against a live scratch Postgres 16, `dbos==2.31.1`: DBOS creates its own `dbos`-schema tables (`workflow_status`, `operation_outputs`, `notifications`, `workflow_events[_history]`, `streams`, `queues`, `workflow_schedules`, `application_versions`, `event_dispatch_kv`, `dbos_migrations`), plus a small `transaction_outputs` table in whichever database is configured as the *application* database. `system_database_url` and `application_database_url` are independently configurable — the system database can be the same database as ours, a separate schema in it, or a fully separate database; DBOS never assumes ownership of the whole database or the connection. Migrations can be split from runtime: `run_dbos_database_migrations(..., application_role=...)` migrates as a DDL-capable role and grants a narrower runtime role afterwards, and `run_migrations=False` fails launch **closed** (not open) if the schema is missing or behind version. Full experiment log: [`../../design/durable-execution.md`](../../design/durable-execution.md) section 4.5.
