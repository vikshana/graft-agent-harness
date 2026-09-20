# Durable Execution & Run Orchestration

> Resolution of the durable-execution deep-dive. Decisions: [ADR-0037 … ADR-0048](../adr/DECISION-INDEX.md#agent).
> Session date: 2026-09-12. Status: 🟢 **Resolved for v1.**
>
> All DBOS behaviour described here was **verified live against `docs.dbos.dev`
> on 2026-09-12**, not recalled. Where a claim is load-bearing, the source page is
> named inline. **The DBOS/LangGraph integration boundary (section 4) was
> additionally confirmed empirically by spike S1 on 2026-09-13 — see the
> Verification sections of [ADR-0039](../adr/agent/0039-the-run-is-the-durable-workflow.md),
> [ADR-0040](../adr/agent/0040-langgraph-is-compiled-with-no-checkpointer.md) and
> [ADR-0041](../adr/agent/0041-step-granularity-is-one-llm-call-or-one-tool-call.md).**
> **System-database placement, RLS interference and PCI scope (section 4.5) were
> further confirmed empirically by spike S2 on 2026-09-13, closing risk X1 (section 8)
> and the last item of section 9's "not yet verified" list — see the Verification
> sections of [ADR-0025](../adr/observability/0025-compliance-regime-for-v1-is-pci-dss.md),
> [ADR-0037](../adr/agent/0037-the-durable-execution-engine-is-dbos-transact.md),
> [ADR-0041](../adr/agent/0041-step-granularity-is-one-llm-call-or-one-tool-call.md),
> [ADR-0048](../adr/agent/0048-a-thin-runtime-seam-isolates-the-durable-execution-engine.md),
> [ADR-0049](../adr/platform/0049-two-independent-regional-deployments.md) and
> [ADR-0050](../adr/tenancy/0050-isolation-is-never-thread-level.md).**

---

## 1. Decision summary

| #       | Decision                                                                                                                                                                                              |
|---------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **E1**  | **Engine: DBOS Transact** — an MIT-licensed library embedded in the worker process, backed by the Postgres we already run. Temporal rejected; option (c) rejected; DBOS Conductor rejected.           |
| **E2**  | **Recovery is identity- and revision-scoped** — a returning matching executor and the immutable released application compatibility revision may restart its own work. Alive-but-silent, ambiguous and stuck Runs produce durable operator escalation; automatic cross-executor takeover is not Phase 1 scope (ADR-0078). |
| **E3**  | **Pattern B primary** — the run *is* the durable workflow. Pattern A (durable-workflow-as-tool) used **only** for write actions.                                                                      |
| **E4**  | **LangGraph keeps no checkpointer.** DBOS step checkpoints are the single source of execution truth.                                                                                                  |
| **E5**  | **Step granularity: one LLM call = one step; one tool call = one step; one sub-agent = one child workflow; one run = one parent workflow.**                                                           |
| **E6**  | **Idempotency: `workflow_id` for run creation, `deduplication_id` for trigger dedupe, `(graft_run_id, step_id, idempotency_key)` for write side effects.** Fork/eval runs are structurally read-only. |
| **E7**  | **Cancellation is at the next step boundary.** No `preemptible` steps in v1.                                                                                                                          |
| **E8**  | **Budgets: queue partition keys for rate/concurrency, workflow deadlines for wall clock, agent + Tool Gateway for semantic breakers.**                                                                |
| **E9**  | **ADR-0033's signal table is replaced by DBOS `send`/`recv`.** ADR-0030's event log is unaffected.                                                                                                    |
| **E10** | **Deploy strategy is blue/green with version pinning**, using an explicit released application compatibility revision. Every release drains all prior cohorts. Bounded by E11's approval expiry. |
| **E11** | **All five durable-timer use cases are in v1**, including a **bounded HITL approval window** — which is what makes E10's drain window finite.                                                         |
| **E12** | **Reversibility is real but bounded, and throughput is not the trigger to watch.** A thin `runtime` seam keeps engine calls out of domain logic. **DBOSify is rejected as a hedge.** See section 10.  |

---

## 2. E1 — Engine choice: DBOS Transact

### 2.1 The constraint that decided it

The session's first answer was categorical: **no paid plan, and no separate orchestration service like Temporal.** That
single constraint resolves the briefing's three-way choice, because:

- **(a) Temporal** requires operating a cluster plus its datastores (typically Cassandra for durability, Elasticsearch
  for visibility) — a second distributed system alongside the application. Excluded by constraint, not by merit.
- **(c) Bare worker + LangGraph checkpoints** was already `Recommended reject` in the briefing and remains rejected. It
  fails the 30-minute and multi-hour-HITL requirements outright.
- **(b) Postgres-backed job runner** is the surviving shape — and DBOS Transact *is* that shape, already built,
  MIT-licensed, and load-tested.

### 2.2 Why this is not "build it ourselves" after all

The briefing costed option (b) at "roughly two weeks of focused work" and warned that "the hard parts … are exactly
where hand-rolled implementations are subtly wrong." DBOS removes essentially all of that surface:

| Briefing section 3 requirement                 | DBOS mechanism                                                                           | Ours to build?      |
|------------------------------------------------|------------------------------------------------------------------------------------------|---------------------|
| Recover graph state after crash                | Step checkpoints in Postgres                                                             | No                  |
| **Work rediscovery**                           | Executor-pinned recovery + Conductor                                                     | **Partly — see E2** |
| **Durable timers**                             | `DBOS.sleep()`, `recv(timeout_seconds=…)`, cron schedules                                | No                  |
| **Cancellation propagation**                   | `cancel_workflow`; `timeout_ms`/`deadline_epoch_ms` cancel workflow **and all children** | No                  |
| **Per-step retry with backoff**                | Step retry policy                                                                        | No                  |
| **Fan-out / fan-in, partial failure**          | Child workflows, handles, `wait_first`                                                   | No                  |
| **Per-queue rate limiting / concurrency caps** | Durable queues, incl. **per-partition** limits                                           | No                  |
| Visibility into in-flight runs                 | `list_workflows`, `list_workflow_steps` (SQL-backed)                                     | No (UI only)        |

Only one row is not free, and it is the direct price of excluding Conductor.

**Note on the durable-execution briefing (closed).** The briefing argued that if durable timers proved *pervasive*,
"that shifts strongly toward Temporal." They did prove pervasive — all five candidates are v1 (section 6.4) — but this
does **not** reopen E1, because DBOS covers every one of them natively (durable sleep, `recv` timeouts, and
database-stored cron schedules that are creatable, pausable and deletable at runtime). The premise held; the conclusion
does not follow for this engine.

### 2.3 What we give up by excluding Conductor

Conductor is DBOS's proprietary, licence-keyed control plane (self-hostable, but still paid — confirmed on
`/production/hosting-conductor`). Excluding it costs:

1. **Automatic cross-executor failover** — deliberately excluded from Phase 1 by ADR-0078; unsafe identity or revision combinations are rejected before resume and escalated durably.
2. **The DBOS Console UI** — dashboards, trace timelines, click-to-fork. The *programmatic* equivalents
   (`list_workflows`, `list_workflow_steps`,
   `fork_workflow`, `resume_workflow`) are all in the MIT library, so this is a convenience loss, not a capability loss.
   Our own operator surface can be built on those APIs, and ADR-0005's OTel pipeline already covers observability
   proper.
3. **Managed retention policies** — we set our own, and ADR-0015 already mandates a retention regime (12 months, 3 hot)
   that we must implement regardless.

### 2.4 Cost of the determinism constraint

The briefing treated determinism as a Temporal-specific downside. **It is not** — DBOS imposes the same rule, for the
same replay reason: the workflow function must be deterministic, and all non-deterministic work (LLM calls, tool calls,
clock reads, randomness) must live inside steps.

This is therefore **not a differentiator**, and it is largely already satisfied by **ADR-0003** ("graph nodes written as
plain functions; no framework types in node signatures") and **ADR-0037**. What it does mean is that ADR-0037 is
upgraded from a recommendation to a hard requirement — see section 4.

---

## 3. E2 — Accepted matching-executor recovery

### 3.1 Accepted boundary

The accepted mechanism is the narrower boundary recorded by [ADR-0078](../adr/agent/0078-phase-1-disables-automatic-cross-executor-recovery.md),
with the released compatibility revision requirement from [ADR-0077](../adr/agent/0077-auto-versioning-must-account-for-dependency-upgrades.md).
Run metadata records the expected executor identity and immutable released
application compatibility revision. The runtime recovery entry point reads that
metadata and rejects a wrong identity or revision before it calls DBOS resume.
Only a returning executor with both values matching may restart the Run.

An alive-but-silent, ambiguous or stuck observation is not converted into a
heartbeat timeout or a cross-executor takeover. It is a typed durable operator
escalation. The escalation record is application evidence and is not a
stdout-only diagnostic.

### 3.2 The mechanism

The runtime seam owns one accepted recovery entry point. It performs the
following sequence with public DBOS APIs:

1. Read insert-once Run metadata containing the expected executor and released
   application compatibility revision.
2. Reject a mismatched executor or revision before invoking `resume_workflow`.
3. For an exact match, invoke the public DBOS resume operation and let the
   matching executor recover its own checkpointed workflow.
4. For alive-but-silent, ambiguous or stuck state, insert one typed durable
   operator escalation record and do not invoke resume.

This does not provide automatic cross-executor recovery and does not treat a
stale heartbeat as permission to take over a Run. StatefulSet identity and
blue/green deployment remain operational placement and drain concerns, not a
cross-executor recovery fence.

### 3.3 Always enqueue, never start directly

All runs are submitted via `enqueue_workflow` onto a durable queue rather than started in-process. An *enqueued*
workflow has no owning executor yet, so the window during which E2's machinery is needed at all is confined to genuinely
in-flight runs. This also buys E8's flow control for free.

---

## 4. E3/E4/E5 — How DBOS and LangGraph compose

### 4.1 Two patterns; we need the one the blog does not show

DBOS's LangGraph material (the Feb-2025 blog post, and the maintained "Reliable Customer Service Agent" example)
demonstrates **Pattern A**: a DBOS workflow exposed as a LangChain `@tool`, with LangGraph remaining the top-level
driver and keeping `PostgresSaver` for agent state.

**Pattern A alone does not solve our problem.** It makes individual tools crash-proof but leaves the *run* with no work
rediscovery — if the pod dies between tool calls, the LangGraph checkpoint sits there and nothing resumes it. It also
runs two checkpointers side by side, which is exactly the double-checkpointing hazard flagged in the briefing.

DBOS's own newest and most relevant example — the **Hacker News Deep Research Agent** — instead demonstrates **Pattern
B**: the agent loop itself is the workflow, sub-investigations are child workflows, each LLM call and tool call is a
step, `set_event` publishes status, `recv` awaits humans. Structurally this is a one-to-one match for our planner →
workers → validator fan-out.

**Decision (E3): Pattern B is the primary structure. Pattern A is retained specifically for write actions** (open a PR,
file a Jira ticket, silence an alert), where a self-contained durable workflow with its own idempotency key is the right
unit and where ADR-0014's approval gate already forces a workflow boundary.

**Known tension, accepted deliberately:** DBOS's Pattern B examples are framework-free Python agent loops, not
LangGraph. Adopting Pattern B demotes LangGraph from "the orchestrator" to "graph structure invoked beneath the
orchestrator." This does not contradict **ADR-0003** — LangGraph + DeepAgents remains the agent framework — but it does
mean the durable orchestration boundary sits *above* the graph, and the graph must be written to be entered and
re-entered at step boundaries. This is ADR-0037, and it is now mandatory rather than advisory.

### 4.2 E4 — no LangGraph checkpointer

LangGraph is compiled **without** a checkpointer. DBOS step checkpoints are the single source of execution truth. This
resolves the briefing's double-checkpointing hazard by elimination rather than by reconciliation: there is no second
state store to diverge.

Conversational state for multi-turn chat runs (ADR-0036 makes chat a first-class run)
lives in our own run-state tables, passed explicitly into the graph — consistent with ADR-0003's "no framework types in
node signatures."

**Eval impact: net positive.** Per ADR-0071 the eval sink is fed by OTel spans (ADR-0008)
and the durable event log (ADR-0030) — never by a checkpointer, which stores state snapshots rather than trajectories.
DBOS additionally provides:

- `list_workflow_steps()` — an ordered, SQL-queryable trajectory with checkpointed step inputs and outputs;
- `fork_workflow(id, from_step=N)` — re-run a historical incident from step *N*
  under a new prompt version, as a **new workflow ID** with history copied, so the original is preserved for comparison.
  This directly serves [`observability-pipeline.md`](./observability-pipeline.md)'s
  "compare prompt v1.2 vs v1.3 across 50 historical incidents," and is strictly better than in-place checkpointer
  time-travel.

The only real loss is LangGraph's interactive state introspection when debugging, which `fork` plus step listing covers.

### 4.3 E5 — step granularity

The briefing called granularity "the crux." The rule:

| Unit                                                                          | Maps to                                                  |
|-------------------------------------------------------------------------------|----------------------------------------------------------|
| A run (chat, dashboard workflow, or RCA — all one primitive per **ADR-0036**) | Parent workflow                                          |
| A sub-agent / DeepAgents worker invocation                                    | Child workflow                                           |
| One LLM call                                                                  | One step                                                 |
| One tool call via the Tool Gateway                                            | One step                                                 |
| One write action                                                              | Child workflow (Pattern A), with its own idempotency key |

Consequences worth stating explicitly:

- **Retry waste is bounded to one LLM call** (accepted in session, Q6).
- **ADR-0033's "signal check at every tool-call boundary" is satisfied structurally**, not by a bespoke hook: since
  every tool call is a step, and cancellation preempts at the next step boundary, the requirement falls out of the
  granularity rule.
- Write amplification is one Postgres write per step, ~1–2 ms — accepted in session (Q3b), and consistent with DBOS's
  published >40K steps/sec benchmark against a single Postgres.
- **Steps must return pointers, not payloads.** Large tool artifacts go to object storage, with the step returning a
  reference — required by DBOS for write-size reasons, and independently required by ADR-0034, which already routes
  artifacts to object storage and fetches them on demand.

### 4.4 Confirmed by spike S1 (2026-09-13)

Sections 4.1–4.3 above were, until 2026-09-13, an untested assumption — ADR-0039 conceded openly that DBOS's Pattern B
references are framework-free Python loops, not LangGraph. **Spike S1** closed that gap with a throwaway prototype
(`dbos==2.31.1`, `langgraph==1.2.11`, `langchain-mcp-adapters==0.3.2`, Postgres 16) and eight experiments; its
confirmation is recorded in the Verification sections
of [ADR-0039](../adr/agent/0039-the-run-is-the-durable-workflow.md),
[ADR-0040](../adr/agent/0040-langgraph-is-compiled-with-no-checkpointer.md) and
[ADR-0041](../adr/agent/0041-step-granularity-is-one-llm-call-or-one-tool-call.md). Result: **outcome (a), works as
designed, no wrapper needed for the boundary itself.**

**Integration pattern.** `graph.ainvoke()` (or `astream()`) called directly from inside a `@DBOS.workflow()` function is
the pattern — there is no need to decompose the graph and drive it node-by-node from the workflow function. DBOS's step
context (`contextvars`-based) survives being invoked through LangGraph's Pregel executor, so ordinary `@DBOS.step()`
-decorated functions called from graph node bodies are correctly recorded as individual steps, in call order, named for
the step-wrapper function rather than the graph node. This was confirmed under crash/resume at three kill points
(mid-LLM-call, mid-tool-call, between steps: no duplicated tool calls on any of them), cancellation at the next step
boundary (ADR-0043), child workflows spawned from inside a graph node, and a real streamable-HTTP MCP tool call
(ADR-0070) — not only against the in-process fakes used for the other experiments.

**Pool-size finding.** Connection count does **not** scale with concurrent workflow count. DBOS opens a fixed-size
SQLAlchemy pool (`pool_size=20, max_overflow=0`, the SDK default) at `DBOS.launch()` time and reuses it across every
workflow started in that process, on both a direct Postgres connection and a pgbouncer transaction-mode pooler. **The
binding scale constraint is therefore the process's configured pool size, not connections × concurrent runs** — a
materially smaller capacity-planning number, but also a hard ceiling with no warning signal from run count alone. Pool
checkout wait time should be instrumented directly rather than inferred from workflow concurrency.

**pgbouncer configuration note.** Standing up a transaction-mode pooler in front of DBOS is not a five-minute
`DATABASE_URL` swap. DBOS needs *two*
Postgres databases (the app database and `<app>_dbos_sys`), and Postgres 16's
`scram-sha-256` password storage does not survive pgbouncer's usual wildcard
`[databases]` auto-configuration — the auto-generated config sources the backend credential from a password hash in
`userlist.txt`, which cannot complete a SCRAM handshake (`wrong password type`). The fix: a hand-written
`pgbouncer.ini` with the plaintext password given directly in the wildcard
`[databases]` line, plus `auth_type = any` (`trust` still requires the connecting user to exist in an auth file, which a
wildcard config with no
`userlist.txt` does not provide). Anyone standing up pgbouncer in front of DBOS in Phase 1 should budget real time for
this.

**`fork_workflow` caller discipline (normative).** `fork_workflow`/
`fork_workflow_async`'s `application_version` keyword defaults to `None`, which is inserted as a literal `NULL` rather
than "use the calling process's own version." A forked workflow with a `NULL` `application_version` matches no running
executor's recovery/dequeue scan and sits `ENQUEUED` forever — silently, with no error or timeout. **Every call to
`fork_workflow[_async]`
must pass `application_version=DBOS.application_version` explicitly.** This is enforced at the `runtime` seam (section
10.5): the seam's `fork(graft_run_id,
step)` helper always supplies it, so application code cannot omit it.

### 4.5 Confirmed by spike S2 (2026-09-13) — system database, RLS interference and PCI scope

Section 8's risk **X1** and section 9's "not yet verified" list both flagged the same open question: does DBOS's system
database coexist with **ADR-0050**'s isolation model and **ADR-0051**'s scoping rule, and does it fall inside
**ADR-0025**'s PCI-DSS scope? **Spike S2** closed both, empirically, against a live scratch Postgres 16 + pgbouncer
(transaction mode), `dbos==2.31.1`, with a non-superuser application role (the docker image's default bootstrap role
is a superuser and silently bypasses RLS — using it would have invalidated every RLS test below). Seven experiments,
E1–E7, plus a topology check E2:

**E1 — inventory.** DBOS creates its own `dbos`-schema tables:
`workflow_status`, `operation_outputs`, `notifications`, `workflow_events`, `workflow_events_history`, `streams`,
`queues`, `workflow_schedules`, `application_versions`, `event_dispatch_kv`, `dbos_migrations` — plus
`transaction_outputs` in whichever database is configured as the *application* database. A representative run (parent
workflow, step, child workflow, `send`/`recv`, queued workflow) showed **every step's return value, every workflow's
input arguments, and every `send`/`set_event` payload persisted in full** as base64-encoded pickle — not a pointer, not
redacted. Table ownership: the connecting application role, same as our own tables — DBOS runs as table owner, not
superuser, and grants itself no special privileges.

**E2 — same database or separate?** `system_database_url` and `application_database_url` are independently
configurable. DBOS was pointed at a fully separate database for its system tables while the application database
stayed put; both launched and ran correctly, with DBOS's control-plane tables confined entirely to the dedicated
database (bar the small `transaction_outputs` table, which always accompanies the *application* database regardless of
topology). **DBOS never requires a shared connection or ownership of the whole database** — one system database per
region (already ADR-0049's stated topology) is fully supported without contortion.

**E3 — RLS interference (the load-bearing result).** Retrofitting `FORCE ROW LEVEL SECURITY` plus a `graft_tenant_id`
policy onto DBOS's own `workflow_status` table — the same pattern used for our own tables — causes DBOS's own `INSERT`
to be **rejected outright by Postgres** (`new row violates row-level security policy`), because DBOS never sets
`graft.tenant_id` and has no column for it: a workflow cannot even start. The only policy shape that avoids the error
(`graft_tenant_id IS NULL OR graft_tenant_id = current_setting(...)`) is vacuous — it grants every Tenant unrestricted
read/write access to every DBOS row, since every DBOS-written row is `NULL`. **Conclusion: RLS on `graft_tenant_id`
cannot be the isolation mechanism for DBOS's own control-plane tables.** ADR-0050 is updated accordingly: isolation for
workflow metadata is enforced at the application layer (the `runtime` seam, section 10.5, is the chokepoint), not by
Postgres, for this specific table set. Our own tables are unaffected.

**E4 — `SET LOCAL` survival under pgbouncer transaction mode.** Our own pattern — `SET LOCAL graft.tenant_id` per
transaction against a `FORCE ROW LEVEL SECURITY` table — was hammered with 400 interleaved, alternating-tenant,
single-statement transactions across 4 threads through pgbouncer in transaction mode: **zero cross-tenant leakage**,
consistent with pgbouncer's transaction-mode contract (it multiplexes at the transaction boundary, the same boundary
`SET LOCAL` resets at). Separately, DBOS itself — including a `send`/`recv` round trip — ran correctly through the same
pooled endpoint with both `use_listen_notify=True` (default, session-scoped `LISTEN`) and `use_listen_notify=False`
(documented polling fallback). This was a single-process smoke test; a multi-worker, production-scale stress test of
DBOS's notification listener under a pooler is still worth doing before fully trusting it at fleet scale.

**E5 — connection behaviour.** 8 backend connections held at idle (two bounded pools, system + app, default
`pool_size=20` each but opened lazily), 25 held for 50 concurrently in-flight workflows (~0.5 connections per in-flight
workflow) — confirming section 4.4's pool-size finding with real numbers, and giving ADR-0048's scale note a concrete
ratio rather than an assumed one.

**E6 — migration story.** `run_migrations=False` against a schema that does not exist yet **fails launch closed**, with
an explicit error naming the required action (`dbos migrate`, or enable migrations) — not a silent no-op.
`run_dbos_database_migrations(system_database_url, app_database_url, schema, application_role=...)` is the out-of-band
equivalent of the `dbos migrate` CLI: it migrates as whatever role runs it, then **grants the runtime role** permissions
on the DBOS schema afterwards — i.e. DBOS explicitly supports "migrate as a DDL-capable role, run as a narrower one,"
which is exactly ADR-0046's blue/green need.

**E7 — PCI determination.** A step was made to deliberately violate ADR-0041's pointer rule, returning a raw string
containing a test PAN. It landed, unmodified, in `workflow_status.inputs`, `workflow_status.output` and
`operation_outputs.output` — recoverable in plaintext with one `SELECT` + `base64.b64decode` + `pickle.loads`. DBOS's
serialisation is a wire format, not encryption or redaction, and there is no PII/PAN-aware filtering anywhere in the
path. **The DBOS system database is confirmed inside PCI-DSS scope** (ADR-0025 updated), and ADR-0041's pointer rule is
promoted from convention to a CI-enforced invariant (`scripts/check_step_pointer_rule.py`).

**Net effect on Phase 1's schema:** one DBOS system database per region (ADR-0049, unchanged, now empirically
confirmed), our own tables keep full `FORCE ROW LEVEL SECURITY` + `SET LOCAL` (ADR-0050, scope clarified), the DBOS
system database is PCI-DSS scope inheriting ADR-0025's scrubbing and ADR-0015's retention, and the pointer rule
(ADR-0041) is now a hard, lint-checked line rather than a design preference. Risk X1 (section 8) is closed.



---

## 5. E6 — Idempotency

Three distinct layers, each with a different key:

| Layer                                                                | Key                                                      | Mechanism                                                                                      |
|----------------------------------------------------------------------|----------------------------------------------------------|------------------------------------------------------------------------------------------------|
| **Run creation** (duplicate webhook, retried API call, double-click) | `workflow_id` set from a caller-supplied idempotency key | Enqueuing twice with the same `workflow_id` yields one run                                     |
| **Trigger dedupe** (alert storm re-firing the same alert)            | `deduplication_id` on the queue                          | Only one workflow with a given dedupe ID may be `ENQUEUED`/`PENDING` on a queue at a time      |
| **Write side effects** (PR, Jira, silence, remediation)              | `(graft_run_id, step_id, idempotency_key)`               | Passed to the Tool Gateway and to the upstream API's own idempotency facility where one exists |

The third layer is the one that carries real production risk and is the reason ADR-0037's "side-effect idempotent"
clause exists. It must survive retry, reconnect, **and** replay-after-fork.

**Fork/eval runs are structurally read-only.** `fork_workflow` deliberately re-executes from a chosen step, so a forked
run replaying an investigation would otherwise re-file its Jira ticket or re-open its PR. Forked runs are therefore
denied write tool classes by the same capability-token mechanism as **ADR-0013** — enforced by the token's contents, not
by a policy check that could be bypassed.

---

## 6. E7/E8/E9/E11 — Cancellation, budgets, signals, timers

### 6.1 E7 — cancellation contract

- **Latency:** bounded by the current step's duration. A cancel arriving mid-way through a 40-second PromQL query takes
  effect when that query returns. Accepted in session (Q4). `preemptible=True` steps are **not** used in v1; they remain
  available if a latency complaint ever materialises.
- **Propagation:** `timeout_ms` / `deadline_epoch_ms` cancel the workflow **and all its children**, so sub-agent
  teardown is native rather than hand-rolled.
- **Teardown scope for v1:** child workflows (sub-agents) and pending queue entries. In-flight tool calls complete and
  are discarded. Phase-2 sandboxes (ADR-0004) will need explicit teardown and are out of scope here.

### 6.2 E8 — where budgets are enforced

The briefing asked whether this is orchestrator, agent, or Tool Gateway. It is deliberately all three, at different
layers:

| Control                                                                  | Enforced by                                                           | Mechanism                                                                                                                                        |
|--------------------------------------------------------------------------|-----------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| Concurrent runs per workspace/tenant                                     | **Orchestrator**                                                      | Durable queue **partition key** = workspace, with per-partition concurrency and rate limits — natively implementing **ADR-0017**'s ceiling chain |
| Per-run wall-clock ceiling                                               | **Orchestrator**                                                      | `timeout_ms` / `deadline_epoch_ms`                                                                                                               |
| Max graph depth (~15 steps), loop breakers (same tool + same args twice) | **Agent**                                                             | Semantic, needs graph context the orchestrator lacks                                                                                             |
| Per-run token/cost cap                                                   | **Agent**, reported via `budget_consumed`/`budget_warning` (ADR-0029) | Needs per-call token accounting                                                                                                                  |
| Per-connection throttles protecting *customer* infrastructure            | **Tool Gateway** (ADR-0007, ADR-0017)                                 | Keyed by connection, independent of workspace quota                                                                                              |

### 6.3 E9 — signal delivery supersedes ADR-0033's provisional mechanism

**ADR-0033** specified a Postgres signal table plus `LISTEN/NOTIFY`, explicitly marked provisional pending this session.
It is replaced by **DBOS `send`/`recv`**:

- `DBOS.send(workflow_id, message, topic)` — persisted, exactly-once from within a workflow; callable from outside the
  worker via `DBOSClient`, or even from PL/pgSQL via `dbos.send_message`.
- `DBOS.recv(topic, timeout_seconds)` — the durable multi-hour HITL wait.

ADR-0033's REST back-channel is **unchanged** — the REST handler now calls `send`
instead of inserting into our own signal table. **ADR-0030's event log is entirely unaffected**, preserving the
briefing's requirement that streaming remain independent of the orchestrator choice. We continue to use our own event
log rather than DBOS's `set_event`/streaming features, keeping ADR-0029/ADR-0030/ADR-0031 intact.

### 6.4 E11 — durable-timer inventory (all v1)

| #     | Use case                      | Mechanism                                                   | Notes                                                                                                                                                                                                                                                                                                                 |
|-------|-------------------------------|-------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **a** | HITL approval wait            | `recv(topic, timeout_seconds)`                              | **Now bounded** — see below. Survives restarts                                                                                                                                                                                                                                                                        |
| **b** | Scheduled / recurring RCA     | `create_schedule` per workspace                             | Runtime-creatable/pausable/deletable, stored in the database — so per-workspace schedules are ordinary data, not config redeploys. **These are `system_initiated` runs and therefore structurally read-only per ADR-0013.** Must carry `tenant_id`/`graft_tenant_id` per ADR-0051 and count against ADR-0017 ceilings |
| **c** | Infra-memory refresh (`*/15`) | `apply_schedules` (static set, applied atomically at start) | [`../backlog/future-sessions.md`](../backlog/future-sessions.md) still defers the memory subsystem itself; only the timer mechanism is settled here                                                                                                                                                                   |
| **d** | Auto-close of stale runs      | Sweeper schedule + per-run expiry                           | **Load-bearing for E10** — see below                                                                                                                                                                                                                                                                                  |
| **e** | Per-run wall-clock deadline   | `deadline_epoch_ms` at enqueue                              | Cancels the run **and all children**. Runaway protection and cancellation propagation in one field                                                                                                                                                                                                                    |

**The (a)+ (d) interaction is the significant one.** ADR-0035 deliberately specifies *no escalation path* for unanswered
approvals — "the run simply waits for its owner to return." Combined with E10's version pinning, an unbounded wait would
pin an old code version alive indefinitely: one forgotten approval could block retiring a deployment colour for weeks.

**Therefore the HITL approval wait is bounded in v1.** An unanswered approval expires via (d), closing the run as
`expired` rather than escalating it — which preserves ADR-0035's "no escalation" stance while making E10's drain window
finite. The expiry duration is a product decision not yet taken; it must exceed a realistic on-call handover (a weekend,
so ≥72h) and is the effective upper bound on how long a deployment colour must be retained.

---

## 7. E10 — Deploy strategy and what "version" means

### 7.1 Explicit compatibility revisions

The release boundary is an **explicit released application compatibility revision**. It is a compatibility identifier
owned by the release process, not a Git commit SHA, image tag, or DBOS's automatic source hash. Every mutually versioned
release receives a new revision, including a release whose workflow source appears unchanged. This is the accepted
ADR-0077 all-release-drain policy: a helper or dependency change must not be able to masquerade as compatible merely
because DBOS's automatic diagnostic value stayed the same.

Every workflow is tagged with the explicit revision it started on, and **DBOS only recovers workflows whose revision
matches the current application revision**. The matching-revision guard is necessary but is not a selective drain
exception: every prior cohort is drained before retirement.

### 7.2 Blue/green and all-prior-cohort drain

For versioning, DBOS explicitly recommends blue/green: launch processes on the new version, keep processes on the old
version running, direct new traffic to the new version, and let the old drain.

Concretely for us:

1. New work is enqueued pinned to the released compatibility revision. Scheduled workflows are also assigned that
   revision by the release controller.
2. Capacity for **every prior cohort** remains available while the new release is introduced. No prior cohort is
   selectively exempted because a source hash appears unchanged.
3. The drain controller checks `PENDING`, `ENQUEUED`, and `DELAYED` work for every prior revision and retains the old
   capacity until all three states are empty.
4. The controller alerts on an orphaned cohort or revision with active work but no live executor. An orphan alert is not
   permission to discard or silently reassign the work.
5. A rollback from B to A is a **reverse drain**: restore A capacity, route new work to A, apply the same three-state
   drain and orphan checks, and retire B only after its work is drained.
6. E11 (d)'s approval expiry bounds how long each drain can take.

**Patching** (`DBOS.patch()` / `deprecate_patch()`) is available as an alternative strategy and is the better tool for
an urgent fix that must reach already-running investigations. It is not the default, because it accumulates conditionals
in workflow code. v1 default is versioning + blue/green; patching is the documented escape hatch.

---

## 8. New risks introduced by this decision

| #      | Risk                                                                                                                                       | Notes                                                                                                                                                                                                        |
|--------|--------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **X1** | ~~DBOS's system database falls into PCI-DSS scope.~~ **Confirmed and closed by spike S2 (section 4.5).** | Step inputs/outputs/`send`/`recv` bodies are checkpointed in recoverable plaintext (pickle+base64, not encryption). **Confirmed in PCI-DSS scope** — extends **ADR-0025**. Mitigated structurally by ADR-0041's pointer rule, now a **CI-enforced invariant** (`scripts/check_step_pointer_rule.py`), not merely a convention. |
| **X2** | Matching-executor restart and durable escalation are load-bearing recovery controls.                                                                 | The accepted runtime entry point must reject wrong identity/revision before resume and persist alive-but-silent, ambiguous and stuck escalation states. |
| **X3** | ~~Workflow code changes break in-flight runs.~~ **Resolved by E10.**                                                                       | Residual: the deploy pipeline must gate colour retirement on a `list_workflows` check, and operators must understand that a structural change plus a long-lived approval keeps a colour alive.               |
| **X4** | Pattern B demotes LangGraph below the durability boundary, and DBOS's Pattern B references are not LangGraph-based.                        | We are the integration point. Prototype the parent-workflow-drives-LangGraph shape early.                                                                                                                    |
| **X5** | Worker placement across GCP + AliCloud is unaddressed.                                                                                     | DBOS queues can restrict which workers run which workflows, which is the likely lever, but multi-region Postgres for the system database is an open topology question for the Deployment session.            |
| **X6** | **Per-workspace cron schedules (E11 b) are a new tenant-scoped resource.**                                                                 | They live in the database and are runtime-mutable, so they need ADR-0051 scoping columns, ADR-0016-style versioned policy treatment, and a ADR-0017 ceiling on schedule count/frequency. Closed by ADR-0058. |
| **X7** | Two colours of workers run concurrently against one system database during every structural deploy.                                        | Doubles peak worker count and Postgres connections during drains; capacity planning must assume it.                                                                                                          |

---

## 9. Verification log (2026-09-12)

Verified live against `docs.dbos.dev` and `dbos.dev`:

- `dbos-transact-py` is **MIT**; self-hosted Conductor is **proprietary, licence-keyed**.
- Distributed recovery without Conductor is **executor-ID-pinned**.
- `cancel_workflow` preempts **at the beginning of the next step**; `preemptible`
  steps exist for immediate async interruption.
- `DBOS.sleep()` is durable; cron schedules are **stored in the database** and can be created, paused, resumed and
  deleted **at runtime**; each firing executes on **exactly one** worker. The release controller assigns scheduled
  workflows the current explicit compatibility revision; DBOS's automatic version value is diagnostic only.
- `send`/`recv` are persisted with exactly-once delivery from workflows.
- `fork_workflow` copies history to a **new workflow ID** and re-runs from a chosen step.
- `dbos.enqueue_workflow` exposes `workflow_id`, `deduplication_id`, `priority`,
  `timeout_ms`, `deadline_epoch_ms`, `queue_partition_key`, `delay_until_epoch_ms`,
  `authenticated_user`, `authenticated_roles`.
- `timeout_ms`/`deadline_epoch_ms` cancel **the workflow and all its children**.
- Partitioned queues apply concurrency and rate limits **per partition**.
- **The accepted release boundary is an explicit released compatibility revision**; matching-revision recovery remains
  required. Blue/green retirement drains all prior revisions by checking `PENDING`, `ENQUEUED`, and `DELAYED` work,
  alerts on orphaned revisions, and uses the same controls for reverse-drain rollback. DBOS's automatic version value is
  retained only as a diagnostic observation, never as the compatibility boundary.
- **Patching** (`DBOS.patch`, `DBOS.deprecate_patch`) requires `enable_patching`
  in config and raises `DBOSUnexpectedStepError` when misused.
- Benchmark claim: **>40K workflows/steps per second** on a single Postgres.
- DBOS maintains a **LangGraph example** ("Reliable Customer Service Agent") and a **Pattern B** deep-research agent
  example; first-party *adapter packages* exist for Pydantic AI, LlamaIndex, OpenAI Agents SDK, Google ADK and Vercel
  AI — **LangGraph has a documented pattern, not an adapter.**
- Corroborating **ADR-0030**: DBOS published *"Postgres LISTEN/NOTIFY Can Actually Scale"* (Jul 2026) — 60K writes/sec
  at millisecond latency.

**Current observed evidence and remaining verification:**

1. The Gate 0.3 runtime lane observed DBOS Python **async** ergonomics with async LangGraph and
   `langchain-mcp-adapters`; this is bounded synthetic integration evidence, not production completion evidence.
2. The version comparison observed automatic runtime/source and schema diagnostics, including a helper-only
   false-compatible result and a DBOS-version difference. These are private/source/schema diagnostics, not public
   compatibility API evidence and not the release boundary.
3. Gate 0.3 accepted-scope evidence records the explicit revision contract, matching-revision recovery, metadata and
   typed escalation behaviour. Operational evidence must separately record all-prior `PENDING`/`ENQUEUED`/`DELAYED`
   drain checks, orphan alerts, and reverse-drain rollback; the bounded experiment is not a production completion claim.

~~Interaction of DBOS system-database migrations with our own Postgres migrations and ADR-0051's row-level security
(DBOS tables are not RLS-aware).~~ **Closed by spike S2** (section 4.5, experiments E3/E6): DBOS's own tables cannot
carry a `graft_tenant_id` RLS policy without breaking DBOS outright, so isolation for workflow metadata is enforced at
the application layer instead; migrations can be run out-of-band by a DDL-capable role separate from the runtime role.

---

## 10. E12 — Reversibility: could we move to Temporal later?

Asked directly in review: *"Is it possible to start with DBOS and later switch to Temporal if scaling becomes an
issue?"* Short answer: **yes, and the migration is bounded — but scaling is almost certainly the wrong trigger to watch
for.**

### 10.1 Interrogating the premise: throughput will not be the binding constraint

Our published workload is **tens of simultaneous runs**, bursty. Under E5's granularity, a run emits roughly one step
per LLM or tool call — call it order-of one step per second per run at the busiest. A hundred concurrent investigations
is therefore on the order of **100 steps/sec**, against DBOS's published **>40K workflows-or-steps/sec on a single
Postgres**. That is roughly **two to three orders of magnitude of headroom**.

Long before the orchestrator saturates, the binding constraints will be:

1. **LLM/GPU capacity** (LiteLLM/vLLM throughput, provider rate limits),
2. **Tool-call limits against customer infrastructure** — the shared K8s control plane that ADR-0017's per-connection
   throttles exist to protect,
3. **Postgres connection count**, not Postgres throughput — aggravated by X7's blue/green doubling, and the one thing
   ADR-0030 already names as its revisit trigger (`LISTEN/NOTIFY` connection scaling).

**Temporal would not help with any of the three.** (3) is mitigated by a pooler such as PgBouncer; (1) and (2) are the
agent's and the Tool Gateway's problem.

And if raw orchestration throughput *did* ever bind, DBOS's own answer is to **shard workflows across multiple Postgres
databases** — for which ADR-0051's
`tenant_id`/`graft_tenant_id` is a natural shard key. That is a materially cheaper escape than changing engines.

### 10.2 The realistic reasons to revisit — none of them are throughput

| Trigger                                            | Assessment                                                                                                                                                                                                                                                                                                                                    |
|----------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Multi-cloud active-active (GCP + AliCloud), X5** | The genuinely hard one. A single system database is a poor fit for active-active across clouds. **But Temporal has the same problem** — its cluster needs a co-located datastore too. The likely answer either way is **one application + one system database per region, with runs pinned to a region**, not a globally shared orchestrator. |
| **Operational maturity / hiring**                  | Temporal is the better-known quantity with a deeper operational corpus. A legitimate reason; unrelated to scale.                                                                                                                                                                                                                              |
| **Postgres connection pressure**                   | Mitigate with a pooler first. Only an engine question if pooling fails.                                                                                                                                                                                                                                                                       |
| **DBOS project health**                            | A young company; the library is MIT and self-hostable, which caps the downside, but it is worth periodic review.                                                                                                                                                                                                                              |

### 10.3 What a migration would actually cost

The briefing's core worry was that the *irreversible* part is graph decomposition, not engine choice. **That worry is
fully discharged:** E5/ADR-0041's granularity rule — run = workflow, sub-agent = child workflow, LLM call = step, tool
call = step — is engine-agnostic and maps one-to-one onto Temporal's workflow / child-workflow / activity model. That is
exactly what ADR-0037 asked for, and it is satisfied whichever engine we run.

Mapping the rest:

| Ours                                    | Temporal equivalent                                                                                                 | Cost                                                                                                                   |
|-----------------------------------------|---------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| E9 `send`/`recv`                        | Signals                                                                                                             | ≈ 1:1                                                                                                                  |
| E11 durable sleep, cron schedules       | Timers, Schedules                                                                                                   | ≈ 1:1                                                                                                                  |
| E6 `workflow_id` / `deduplication_id`   | Workflow ID + reuse policy                                                                                          | ≈ 1:1                                                                                                                  |
| E7 deadlines cancelling children        | Workflow timeouts + cancellation scopes                                                                             | ≈ 1:1                                                                                                                  |
| **E2 matching-executor/revision restart + durable escalation** | **Worker identity plus versioned deployment controls** | **Requires explicit runtime and operator-record implementation** |
| E10 blue/green version pinning          | Worker versioning / build IDs                                                                                       | Conceptually similar, mechanically different                                                                           |
| **E8 per-partition queue flow control** | **No direct equivalent** — DBOS's own comparison notes Temporal lacks comparable queueing/flow-control abstractions | **Real rework.** ADR-0044's per-workspace concurrency/rate limits (ADR-0017's ceiling chain) would need reimplementing |
| **E4 `fork_workflow` for evals**        | Reset is roughly analogous but not identical                                                                        | **Partial rework** of the prompt-comparison eval flow                                                                  |

So a migration is **moderate, bounded and mostly mechanical**, with exactly two areas of genuine rework: per-workspace
flow control, and the fork-based eval loop. Both are areas where DBOS is *better* than Temporal for us — which is a
further argument that migration pressure is unlikely to come from capability.

### 10.4 DBOSify as a hedge — considered and rejected

**DBOSify** (`pip install dbosify`) is a drop-in replacement for the **Temporal Python SDK** backed by Postgres via DBOS
Transact: you `import dbosify` instead of
`temporalio`, and point clients and workers at a connection string instead of a Temporal server. It supports workflows,
activities, signals, updates, queries, retries and recovery.

It is marketed for Temporal → DBOS, but it structurally enables the reverse hedge:
**write against the Temporal SDK API now, run it on Postgres, and "switch to Temporal" later by changing imports and
pointing at a server.**

**Rejected, for three reasons:**

1. **It forces a lowest-common-denominator design.** Writing to the Temporal API surface forfeits precisely the
   DBOS-native features this design is built on —
   `queue_partition_key` flow control (E8/ADR-0044), `fork_workflow` (E4/ADR-0040),
   `deduplication_id` (E6), runtime-mutable database-stored schedules (E11), and
   `list_workflow_steps` trajectories. We would pay the migration cost *up front, permanently*, to insure against an
   event section 10.1 shows is unlikely.
2. **It is a young, Python-only compatibility layer** in the critical path of the least-reversible component in the
   system, with partial feature compatibility documented in its own `ARCHITECTURE.md`.
3. **It insures the wrong risk.** Section 10.2 shows the plausible trigger is topology (multi-cloud), which DBOSify does
   nothing for.

### 10.5 What we do instead: a thin `runtime` seam

Not a `RunController` driver port — that idea (ADR-0037's original framing) is unworkable in practice, because DBOS's
value comes from decorators applied to our own functions, and determinism constraints cannot be hidden behind an
interface. A wrapper pretending otherwise would be leaky and would buy little.

Instead, a **single small internal module** through which all engine interaction flows, so that domain and agent code
never imports `dbos` directly:

- `enqueue_run(...)` → `enqueue_workflow` with workflow ID, dedupe ID, partition key, deadline
- `await_human(graft_run_id, timeout)` → `recv`
- `signal(graft_run_id, message)` → `send`
- `sleep_until(...)` → `DBOS.sleep`
- `cancel(graft_run_id)`, `resume(graft_run_id)`,
  `fork(graft_run_id, step)` → `fork_workflow`, **always passing
  `application_version=DBOS.application_version` explicitly** (see section 4.4 — the SDK's own default silently produces
  a permanently
  `ENQUEUED`, un-recoverable forked workflow)
- `list_runs(...)`, `list_steps(graft_run_id)`

This is worth doing **regardless of migration**: it is the natural chokepoint for ADR-0015 audit emission, ADR-0029
event publication, ADR-0051 tenant scoping and ADR-0017 ceiling checks, and it makes the engine testable by
substitution. It is hygiene that happens to also cap migration cost — not an abstraction built on speculation.

**It does not, and is not meant to, make the engine swappable by configuration.**
The `@DBOS.workflow()` / `@DBOS.step()` decorators stay on our functions. Swapping engines means re-decorating and
rewriting section 10.3's two rework areas. That is the honest, bounded cost, accepted.
