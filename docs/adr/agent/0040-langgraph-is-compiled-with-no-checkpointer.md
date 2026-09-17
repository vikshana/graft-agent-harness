---
id: ADR-0040
title: LangGraph is compiled with no checkpointer
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
legacy_id: D40
---

# ADR-0040 — LangGraph is compiled with no checkpointer

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D40`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

ADR-0039 puts the durability boundary above the LangGraph graph, using DBOS step checkpoints as the workflow's execution
record. If LangGraph also kept its own checkpointer for agent state, a run would carry two independent state stores that
could diverge after a crash — the double-checkpointing hazard the durable-execution deep-dive (referenced as `04`
section 6.7) flagged. Conversational, multi-turn runs (ADR-0036) still need somewhere for chat state to live, and the
eval pipeline (ADR-0071) needs a queryable trajectory to compare prompt versions against historical incidents.

## 2. Decision

**LangGraph is compiled with no checkpointer.** DBOS step checkpoints are the single source of execution truth,
resolving `04` section 6.7's double-checkpointing risk **by elimination**. Conversational state for multi-turn chat runs
(ADR-0036) lives in our own run-state tables, passed explicitly into the graph per ADR-0003. **Eval impact is net
positive**, not a loss: per ADR-0071 the eval sink was never fed by the checkpointer (a state store, not a trajectory
store) but by OTel spans (ADR-0008) and the event log (ADR-0030). DBOS adds `list_workflow_steps()` (an ordered,
SQL-queryable trajectory) and **`fork_workflow(id, from_step=N)`**, which re-runs a historical incident from step *N*
under a new prompt version as a **new workflow ID** with history copied — directly serving section 3's "compare prompt
v1.2 vs v1.3 across 50 historical incidents", and strictly better than in-place checkpointer time-travel.

## 3. Considered options

| Option                                                                             | Verdict     | Why                                                                                                                                                                                                                                              |
|------------------------------------------------------------------------------------|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **No LangGraph checkpointer; DBOS step checkpoints are the sole execution record** | ✅ Chosen   | Eliminates the double-checkpointing hazard by construction rather than by reconciliation                                                                                                                                                         |
| Keep `PostgresSaver` alongside DBOS's step checkpoints                             | ❌ Rejected | Two independent state stores with no defined precedence on divergence after a crash                                                                                                                                                              |
| Rely on the LangGraph checkpointer as the eval trajectory source                   | ❌ Rejected | Per ADR-0071 the eval sink was never fed by the checkpointer (a state-snapshot store, not a trajectory store) — it needs OTel spans (ADR-0008) and the event log (ADR-0030), which DBOS's `list_workflow_steps()`/`fork_workflow` serve directly |

## 4. Consequences

- **Positive —** eval impact is net positive, not a loss: DBOS's `list_workflow_steps()` gives an ordered, SQL-queryable
  trajectory, and `fork_workflow(id, from_step=N)` re-runs a historical incident under a new prompt version as a new
  workflow ID with history copied — strictly better than in-place checkpointer time-travel.
- **Negative / accepted trade —** conversational state for multi-turn runs must be carried explicitly through our own
  run-state tables into the graph (ADR-0003's "no framework types in node signatures"), rather than relying on
  LangGraph's built-in state persistence.
- **Follow-on work —** the `runtime` seam's `fork()` helper must always pin `application_version` when calling
  `fork_workflow` — the SDK's own default silently strands the forked run (see Verification).
- **Revisit trigger —** none observed.

## 5. Verification

- Confirmed by **spike S1** (2026-09-13, experiments E1/E3/E5): no LangGraph checkpointer was needed for correct
  crash/resume or cancellation. `fork_workflow` correctly reuses steps before the fork point and re-executes from it —
  but only when `application_version=DBOS.application_version` is passed explicitly; its default (`None`) is inserted as
  a literal `NULL` and the forked run never resumes. Mechanism and the full experiment log: [
  `../../design/durable-execution.md`](../../design/durable-execution.md) section 4.4.
