# Open Question 04 — Durable Execution & Run Orchestration

> **Purpose of this document.** Self-contained briefing for a dedicated deep-dive
> session. Nothing here is decided.
>
> Source research: `docs/research/execution-guardrails.md`,
> `docs/research/session.md`, `docs/research/oversight.md`,
> `docs/research/critique.md`.
> Related: `02-streaming-and-events.md` (signal delivery, cancel semantics).
>
> **This is assessed as the highest-stakes, least-reversible decision in the
> design.** Everything else in the architecture sits behind a swappable port.
> This one shapes how the agent graph itself is decomposed.

---

## 1. The workload being orchestrated

| Property | Value |
|---|---|
| Chat runs | seconds |
| Simple RCA | 30–90 seconds |
| **Multi-agent deep investigation** | **up to ~30 minutes** |
| **HITL pause awaiting human approval** | **minutes to many hours** |
| Concurrency | tens of simultaneous runs; bursty (incident cascades fire many alerts at once) |
| Structure | LangGraph + DeepAgents, with **sub-agent fan-out** (planner → workers → validator) |
| Side effects | tool calls against production systems, some of them **writes** (PRs, Jira tickets, alert silences, and later remediations) |

Triggers: user in UI, user in Slack, or an unattended webhook — including at 03:00
with no human present.

---

## 2. What is already settled

- **D3** LangGraph + DeepAgents is the agent framework. Not in question.
- **D6** Streaming is decoupled via a durable event log. **Therefore the
  orchestrator choice has no effect on streaming.** The worker publishes to the
  log; the gateway tails the log. This is why streaming can be designed
  independently.
- **R8** (pending) The graph should be decomposed into activity-sized,
  individually retryable, side-effect-idempotent steps from day one.

---

## 3. The actual problem: state durability ≠ execution durability

LangGraph's Postgres checkpointer (`AsyncPostgresSaver`) is frequently assumed to
solve this. It does not. It gives **state durability** — the graph state is
recoverable. It does **not** give **execution durability**:

| Capability | LangGraph checkpointer | Needed here? |
|---|---|---|
| Recover graph state after crash | ✅ | ✅ |
| **Work rediscovery** — something re-queues an orphaned run | ❌ Checkpoint sits there forever; nothing resumes it | ✅ Critical — a pod OOM-killed at minute 22 must not silently lose a 30-minute investigation |
| **Durable timers** — wait 6h for approval, then time out and escalate | ❌ A blocked coroutine dies with the pod | ✅ HITL pauses span hours |
| **Cancellation propagation** — kill sub-agents, drain in-flight tool calls, tear down resources | ❌ | ✅ "Cancel RCA" is an explicit requirement in `critique.md` |
| **Per-step retry with backoff** | ❌ | ✅ Flaky infra APIs during an outage is the normal case, not the exception |
| **Fan-out / fan-in with partial-failure semantics** | Partial | ✅ DeepAgents sub-agents |
| **Per-queue rate limiting / concurrency caps** | ❌ | ✅ Directly mitigates the control-plane-DDoS risk from `critique.md` |
| Visibility into in-flight runs | ❌ | ✅ Ops requirement |

Building all of the above by hand is approximately reimplementing a durable
execution engine.

---

## 4. The three options

### (a) Temporal now

Idiomatic shape: **Temporal workflow = orchestration, HITL signals, timers,
fan-out; each LangGraph node or sub-agent invocation = an activity** with
heartbeating for long steps.

*Pros:* correct semantics for every row in the table above, out of the box.
Signals give a clean cancel/steer path. Durable timers handle multi-hour HITL
properly. Child workflows map naturally onto sub-agents. Task-queue rate limiting
is a first-class feature. Strong operational visibility.

*Cons:* significant operational dependency (Temporal cluster + its own datastore)
in an already large stack. Workflow code must be **deterministic**, which is a
real constraint and a real source of subtle bugs. Activities should be bounded,
so a 30-minute LangGraph run cannot simply be "one activity" — it forces the
decomposition described below. Team learning curve.

### (b) Postgres-backed job runner behind a `RunController` port

Build: job table + lease + heartbeat + reaper for orphaned runs + cancel flag +
signal table + retry policy. Roughly two weeks of focused work. Define a
`RunController` port (`start` / `cancel` / `signal` / `await_human` / `schedule`)
so a Temporal driver can be swapped in later.

*Pros:* no new infrastructure (Postgres is already required). Full control.
Cheaper to operate. The port preserves optionality.

*Cons:* you are building a small durable-execution engine, and the hard parts
(exactly-once-ish semantics, lease expiry races, timer accuracy, cancellation
during a tool call) are exactly where hand-rolled implementations are subtly
wrong. **The non-portable part is activity granularity** — if the graph isn't
already decomposed into bounded, retryable, idempotent steps, migrating to
Temporal later means redesigning the graph, not swapping a driver.

### (c) Bare worker + LangGraph checkpoints

*Pros:* cheapest; ships fastest.

*Cons:* loses runs on pod eviction; cannot do multi-hour HITL reliably; no
cancellation; no retry policy; no rate limiting. **Recommended reject** — it fails
the stated 30-minute / multi-hour-HITL requirements outright.

---

## 5. Current leaning

**(b), but with the graph decomposed from day one** into steps that are:

1. **bounded** — no step runs for 30 minutes; long work is many steps,
2. **individually retryable** — a failed step can re-run without corrupting state,
3. **side-effect idempotent** — keyed by `(run_id, step_id, idempotency_key)`, so
   a retry never double-creates a PR or double-executes a remediation,
4. **free of framework types in signatures** — consistent with D3's note that
   graph nodes are plain functions.

With that discipline, the Temporal migration becomes a driver swap. Without it,
it becomes a rewrite. The decomposition is the thing that must be decided now;
the engine itself can follow later.

**Explicitly reject (c).**

---

## 6. Open questions to resolve in the deep dive

1. **Is the two-week build of (b) actually cheaper than operating Temporal**,
   given the stack already includes Postgres, Redis, Qdrant, Keycloak, a
   Collector, Langfuse, LiteLLM and vLLM? There is a credible argument that one
   more well-understood managed component beats a bespoke half-implementation.
2. **Does anything require durable timers *beyond* HITL?** Scheduled RCA,
   periodic infra-memory refresh (`*/15 * * * *` in the research config),
   approval escalation, auto-close of stale investigations. If timers are
   pervasive, that shifts strongly toward Temporal.
3. **How does a signal reach an in-flight worker** under (b)? Polling a signal
   table (simple, adds latency) vs Redis pub/sub to the worker (fast, not durable)
   vs both. Couples directly to `02-streaming-and-events.md` B5.
4. **Cancellation latency requirement.** Must a 30-minute run stop within
   seconds? What must be torn down — sub-agents, in-flight tool calls, Phase-2
   sandboxes, pending PR drafts?
5. **What is the right step granularity?** Per LangGraph node? Per tool call? Per
   sub-agent invocation? Too fine means checkpoint write amplification and
   latency; too coarse means retries redo expensive LLM work. This is the crux.
6. **Idempotency key design** for write actions — must survive retry, reconnect,
   and duplicate webhook delivery. `streaming.md` flags this as the issue that
   actually matters for an SRE agent.
7. **Interaction with LangGraph's own checkpointer** — do we keep it as the state
   store and layer execution durability on top (likely), or does the orchestrator
   own state entirely? Double-checkpointing is a real risk of duplicated,
   divergent state.
8. **Budget/circuit-breaker enforcement point** — max graph depth (~15 steps),
   per-run cost caps, and loop breakers (same tool + same args twice in a row →
   break and escalate to human) per `oversight.md`. Are these enforced by the
   orchestrator, the agent, or the Tool Gateway? Probably more than one, which
   needs deliberate placement rather than accident.
9. **Worker placement** in a multi-cloud active-active topology (GCP + AliCloud,
   agents kept close to the logs to avoid egress cost) — does the orchestrator
   need to be region/cloud-aware when dispatching?

---

## 7. What a good outcome looks like

1. A decision between (a) and (b), with honest accounting of operational cost.
2. A defined `RunController` port, whichever engine is chosen.
3. A step-granularity rule the graph will be written against.
4. An idempotency scheme for all write actions.
5. A cancellation contract (latency, teardown scope, guarantees).
6. A statement of where budgets, depth limits and circuit breakers are enforced.
7. Confirmation that streaming remains entirely independent of this choice.

---

## 8. Things to verify before deciding (do not assume)

- Whether current LangGraph/DeepAgents versions have added any execution-durability
  features (work rediscovery, durable timers) that would change this analysis.
- Temporal's Python SDK ergonomics with async LangGraph, and how painful the
  determinism constraint is in practice when the workflow only orchestrates.
- Whether any existing OSS project already does "durable execution for LangGraph"
  well enough to adopt rather than build.
- Realistic operational burden of a self-hosted Temporal cluster on GKE/ACK.
