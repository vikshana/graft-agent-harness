# S1 — DBOS × async LangGraph × `langchain-mcp-adapters`

> **Gates: Phase 1 and C4 L3. Timebox: 5 days.**
> Highest-stakes spike in the backlog — it can invalidate the three least
> reversible decisions we have made.

---

## 1. The question

**Can a LangGraph graph execute *beneath* a DBOS workflow boundary, in async
Python, with one DBOS step per LLM call and one DBOS step per tool call, using
`langchain-mcp-adapters` pointed at a single MCP endpoint — without fighting
determinism and without a second checkpointer?**

## 2. Why this blocks everything

ADR-0039 makes the concession openly:

> *"DBOS's Pattern B references are framework-free Python loops, not LangGraph,
> so LangGraph is demoted from 'the orchestrator' to 'graph structure invoked
> beneath the durability boundary.'"*

That is an **untested assumption** underneath three decisions that ADR-0048
identifies as the least reversible work in the project:

| If this fails | These are wrong |
|---|---|
| Graph cannot run under a workflow boundary | ADR-0039 (run = durable workflow) |
| Steps cannot be per-call | ADR-0041 (step granularity) — and ADR-0033's cancel guarantee, which ADR-0041 satisfies *structurally* |
| A checkpointer turns out to be required | ADR-0040 (no checkpointer) — reopening the double-checkpointing hazard |

ADR-0048 assessed migration cost on the assumption that step granularity maps
1:1 onto another engine. **That assessment is only valid if the granularity is
achievable in the first place.**

## 3. Constraints — do not relitigate

These are locked. The spike tests whether they *compose*, not whether they were
right.

| Constraint | ADR |
|---|---|
| Engine is DBOS Transact, embedded library on our Postgres. Temporal and DBOS Conductor are excluded by explicit product constraint (no paid plans, no separate orchestration service) | ADR-0037 |
| Run = parent workflow; sub-agent = child workflow | ADR-0039 |
| 1 LLM call = 1 step; 1 tool call = 1 step | ADR-0041 |
| LangGraph compiled with **no checkpointer**; conversational state lives in our own tables, passed explicitly into the graph | ADR-0040 |
| Steps return **pointers, never large payloads** | ADR-0041 |
| Only the internal `runtime` module imports `dbos` | ADR-0048 |
| The agent points at **exactly one** MCP endpoint (the Tool Gateway) | ADR-0007 |
| Workflow functions are deterministic; all I/O lives in steps | ADR-0037 |
| Pattern A (durable-workflow-as-`@tool`) is retained **only** for write actions | ADR-0039 |

## 4. Method

Build the smallest thing that exercises the real shape. **Do not build the
product.** A fake LLM and a fake MCP server are fine for everything except
experiment 6.

### E1 — The boundary
A DBOS workflow that invokes a 3-node LangGraph (plan → tool → summarise), async
throughout. Each LLM call and each tool call wrapped as a DBOS step.

**Watch for:** who owns the loop. LangGraph wants to drive; DBOS wants to drive.
Does `graph.ainvoke()` / `astream()` work from inside a workflow function, or
does the graph need to be decomposed and driven node-by-node from the workflow?
*This is the crux — record the answer precisely.*

### E2 — Step granularity
Confirm `list_workflow_steps()` returns one entry per LLM call and per tool call
— **not** one per graph node, and not one per whole graph run.

### E3 — Crash and resume
Kill the worker mid-run, at three points: mid-LLM-call, mid-tool-call, between
steps. Confirm resume, and confirm **no duplicated tool calls** on replay.

### E4 — Child workflows
Spawn a sub-agent as a DBOS child workflow from inside a graph node. Confirm
parent/child relationship, and that ADR-0043's cancellation propagates to
children natively.

### E5 — Cancellation
Cancel during an in-flight tool call. Confirm it lands at the next step
boundary, per ADR-0043's contract.

### E6 — MCP wiring
`langchain-mcp-adapters` against **one** real streamable-HTTP MCP endpoint
(ADR-0070). Confirm individual tool invocations can be wrapped as steps rather
than the adapter hiding them inside a single opaque call.

### E7 — Async and pooling
DBOS decorators against async node functions; behaviour under a transaction-mode
pooler. ADR-0048 named **Postgres connection count** the binding scale
constraint, so measure connections held per concurrent run.

### E8 — Fork
`fork_workflow(id, from_step=N)` on a completed run. Confirm it re-executes from
step N — this is the eval loop ADR-0040 promised.

## 5. Outcomes and what each means

| Outcome | Action |
|---|---|
| **(a) Works as designed** | Confirm ADR-0039/0040/0041 with a `verified:` date. Record the integration pattern in [`../../design/durable-execution.md`](../../design/durable-execution.md). Phase 1 proceeds |
| **(b) Works, but needs a wrapper/adapter** | Same, plus document the wrapper as the canonical pattern. Check it does not leak `dbos` imports past the `runtime` seam (ADR-0048) |
| **(c) Per-call granularity impossible; only per-graph-run** | **ADR-0041 must be superseded.** Cancel latency (ADR-0033/0043) and retry-waste bounds both change. Escalate before writing Phase 1 code |
| **(d) LangGraph and DBOS cannot compose at all** | Escalate immediately. Options: Pattern A as primary (explicitly rejected in ADR-0039 — reopen with evidence), drop LangGraph for a framework-free loop (ADR-0003 affected), or revisit ADR-0037's engine under the standing product constraint |

**Outcomes (c) and (d) are findings, not failures.** Discovering them in a
5-day spike is the entire point; discovering them in Phase 2 is the expensive
version.

## 6. Deliverables

1. A throwaway prototype on a branch, with the eight experiments runnable.
2. **One ADR** — confirming or superseding ADR-0039/0040/0041.
3. An update to [`../../design/durable-execution.md`](../../design/durable-execution.md)
   recording the integration pattern and the connection-per-run measurement.
4. Delete this file.

## 7. Out of scope

Real prompts, real investigation quality, the Tool Gateway's authorization
layers, streaming to a surface, multi-tenancy. This spike answers *does the
execution substrate hold together* — nothing else.
