---
id: ADR-0040
title: LangGraph is compiled with no checkpointer
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
legacy_id: D40
---

# ADR-0040 — LangGraph is compiled with no checkpointer

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D40`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**LangGraph is compiled with no checkpointer.** DBOS step checkpoints are the single source of execution truth, resolving `04` section 6.7's double-checkpointing risk **by elimination**. Conversational state for multi-turn chat runs (ADR-0036) lives in our own run-state tables, passed explicitly into the graph per ADR-0003. **Eval impact is net positive**, not a loss: per ADR-0071 the eval sink was never fed by the checkpointer (a state store, not a trajectory store) but by OTel spans (ADR-0008) and the event log (ADR-0030). DBOS adds `list_workflow_steps()` (an ordered, SQL-queryable trajectory) and **`fork_workflow(id, from_step=N)`**, which re-runs a historical incident from step *N* under a new prompt version as a **new workflow ID** with history copied — directly serving section 3's "compare prompt v1.2 vs v1.3 across 50 historical incidents", and strictly better than in-place checkpointer time-travel.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
