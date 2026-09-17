---
id: ADR-0039
title: The run is the durable workflow
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
legacy_id: D39
---

# ADR-0039 — The run is the durable workflow

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D39`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

ADR-0037 fixes the durable-execution engine as DBOS Transact. DBOS's own published LangGraph integration material
demonstrates a single pattern: a DBOS workflow exposed as a LangChain `@tool`, with LangGraph remaining the top-level
driver and keeping its own `PostgresSaver` checkpointer. That pattern makes individual *tools* crash-safe, but leaves
the *run* itself with no work rediscovery — if the pod dies between tool calls, the LangGraph checkpoint sits there and
nothing resumes it — and it runs two checkpointers side by side. A run needs to be resumable as a whole, not merely
tool-call-safe, which forces a choice about which loop is the durable one: the individual tool, or the run.

## 2. Decision

**The run *is* the durable workflow ("Pattern B").** Parent workflow = run; child workflow = sub-agent/DeepAgents
worker; step = one LLM call or one tool call. **"Pattern A" (durable-workflow-as-LangChain-`@tool`) — which is what
DBOS's own LangGraph blog and maintained LangGraph example demonstrate — is retained only for write actions** (PR, Jira,
alert silence), where a self-contained workflow with its own idempotency key is the right unit and ADR-0014's approval
gate already forces a boundary. Pattern A alone was **rejected as primary**: it makes individual tools crash-proof but
leaves the *run* with no work rediscovery, and runs two checkpointers side by side. **Accepted tension:** DBOS's Pattern
B references are framework-free Python loops, not LangGraph, so LangGraph is demoted from "the orchestrator" to "graph
structure invoked beneath the durability boundary." Does not contradict ADR-0003; does make R8 mandatory.

## 3. Considered options

| Option                                                                                                | Verdict                | Why                                                                                                                                                                |
|-------------------------------------------------------------------------------------------------------|------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Pattern B — the run is the durable workflow; sub-agent = child workflow; step = one LLM/tool call** | ✅ Chosen              | Gives the *run* work rediscovery, not just individual tools, with a single checkpointer (DBOS's own step checkpoints)                                              |
| Pattern A alone — durable-workflow-as-`@tool`, LangGraph as top-level driver with `PostgresSaver`     | ❌ Rejected as primary | Crash-proofs individual tools but not the run; runs two checkpointers side by side, which is exactly the double-checkpointing hazard this session set out to avoid |
| Pattern A, scoped to write actions only (PR, Jira, alert silence)                                     | ✅ Chosen, scoped      | A self-contained workflow with its own idempotency key is the right unit where ADR-0014's approval gate already forces a boundary                                  |

## 4. Consequences

- **Positive —** run-level crash/resume without a second checkpointer; sub-agents get crash-safety for free as child
  workflows.
- **Negative / accepted trade —** DBOS's own Pattern B references are framework-free Python loops, not LangGraph.
  Adopting Pattern B demotes LangGraph from "the orchestrator" to "graph structure invoked beneath the durability
  boundary." Does not contradict ADR-0003.
- **Follow-on work —** R8 (framework-free-loop discipline) becomes mandatory rather than advisory: the graph must be
  written so it can be entered and re-entered at step boundaries (ADR-0037).
- **Revisit trigger —** none observed; the boundary was confirmed to compose cleanly by spike S1 (see Verification).

## 5. Verification

- Confirmed empirically by **spike S1** (2026-09-13): `graph.ainvoke()` composes cleanly inside a `@DBOS.workflow()`
  function, with no manual node-by-node driving required, and crash/resume at three kill points (mid-LLM-call,
  mid-tool-call, between steps) resumed cleanly with no duplicated tool calls. Mechanism and the full experiment log: [
  `../../design/durable-execution.md`](../../design/durable-execution.md) section 4.4.
