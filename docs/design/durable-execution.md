# Durable Execution & Run Orchestration

> Resolution of [`../adr/open-questions/04-durable-execution.md`](../adr/open-questions/04-durable-execution.md).
> Session date: 2026-09-12. Status: 🟢 **Resolved for v1.**
>
> All DBOS behaviour described here was **verified live against `docs.dbos.dev`
> on 2026-09-12**, not recalled. Where a claim is load-bearing, the source page is
> named inline.

---

## 1. Decision summary

| # | Decision |
|---|---|
| **E1** | **Engine: DBOS Transact** — an MIT-licensed library embedded in the worker process, backed by the Postgres we already run. Temporal rejected; option (c) rejected; DBOS Conductor rejected. |
| **E2** | **Work rediscovery is ours to build** — a ~150-line heartbeat + reaper, because Conductor is excluded. Workers are a StatefulSet with stable executor IDs, deployed **blue/green** (see E10). |
| **E3** | **Pattern B primary** — the run *is* the durable workflow. Pattern A (durable-workflow-as-tool) used **only** for write actions. |
| **E4** | **LangGraph keeps no checkpointer.** DBOS step checkpoints are the single source of execution truth. |
| **E5** | **Step granularity: one LLM call = one step; one tool call = one step; one sub-agent = one child workflow; one run = one parent workflow.** |
| **E6** | **Idempotency: `workflow_id` for run creation, `deduplication_id` for trigger dedupe, `(graft_run_id, step_id, idempotency_key)` for write side effects.** Fork/eval runs are structurally read-only. |
| **E7** | **Cancellation is at the next step boundary.** No `preemptible` steps in v1. |
| **E8** | **Budgets: queue partition keys for rate/concurrency, workflow deadlines for wall clock, agent + Tool Gateway for semantic breakers.** |
| **E9** | **D33's signal table is replaced by DBOS `send`/`recv`.** D30's event log is unaffected. |
| **E10** | **Deploy strategy is blue/green with version pinning**, using DBOS's auto-computed application version. Bounded by E11's approval expiry. |
| **E11** | **All five durable-timer use cases are in v1**, including a **bounded HITL approval window** — which is what makes E10's drain window finite. |
| **E12** | **Reversibility is real but bounded, and throughput is not the trigger to watch.** A thin `runtime` seam keeps engine calls out of domain logic. **DBOSify is rejected as a hedge.** See §10. |

---

## 2. E1 — Engine choice: DBOS Transact

### 2.1 The constraint that decided it

The session's first answer was categorical: **no paid plan, and no separate
orchestration service like Temporal.** That single constraint resolves the
briefing's three-way choice, because:

- **(a) Temporal** requires operating a cluster plus its datastores (typically
  Cassandra for durability, Elasticsearch for visibility) — a second distributed
  system alongside the application. Excluded by constraint, not by merit.
- **(c) Bare worker + LangGraph checkpoints** was already `Recommended reject` in
  the briefing and remains rejected. It fails the 30-minute and multi-hour-HITL
  requirements outright.
- **(b) Postgres-backed job runner** is the surviving shape — and DBOS Transact
  *is* that shape, already built, MIT-licensed, and load-tested.

### 2.2 Why this is not "build it ourselves" after all

The briefing costed option (b) at "roughly two weeks of focused work" and warned
that "the hard parts … are exactly where hand-rolled implementations are subtly
wrong." DBOS removes essentially all of that surface:

| Briefing §3 requirement | DBOS mechanism | Ours to build? |
|---|---|---|
| Recover graph state after crash | Step checkpoints in Postgres | No |
| **Work rediscovery** | Executor-pinned recovery + Conductor | **Partly — see E2** |
| **Durable timers** | `DBOS.sleep()`, `recv(timeout_seconds=…)`, cron schedules | No |
| **Cancellation propagation** | `cancel_workflow`; `timeout_ms`/`deadline_epoch_ms` cancel workflow **and all children** | No |
| **Per-step retry with backoff** | Step retry policy | No |
| **Fan-out / fan-in, partial failure** | Child workflows, handles, `wait_first` | No |
| **Per-queue rate limiting / concurrency caps** | Durable queues, incl. **per-partition** limits | No |
| Visibility into in-flight runs | `list_workflows`, `list_workflow_steps` (SQL-backed) | No (UI only) |

Only one row is not free, and it is the direct price of excluding Conductor.

**Note on briefing §6.2.** The briefing argued that if durable timers proved
*pervasive*, "that shifts strongly toward Temporal." They did prove pervasive —
all five candidates are v1 (§6.4) — but this does **not** reopen E1, because DBOS
covers every one of them natively (durable sleep, `recv` timeouts, and
database-stored cron schedules that are creatable, pausable and deletable at
runtime). The premise held; the conclusion does not follow for this engine.

### 2.3 What we give up by excluding Conductor

Conductor is DBOS's proprietary, licence-keyed control plane (self-hostable, but
still paid — confirmed on `/production/hosting-conductor`). Excluding it costs:

1. **Automatic cross-executor failover** — addressed by E2.
2. **The DBOS Console UI** — dashboards, trace timelines, click-to-fork. The
   *programmatic* equivalents (`list_workflows`, `list_workflow_steps`,
   `fork_workflow`, `resume_workflow`) are all in the MIT library, so this is a
   convenience loss, not a capability loss. Our own operator surface can be built
   on those APIs, and D5's OTel pipeline already covers observability proper.
3. **Managed retention policies** — we set our own, and D15 already mandates a
   retention regime (12 months, 3 hot) that we must implement regardless.

### 2.4 Cost of the determinism constraint

The briefing treated determinism as a Temporal-specific downside. **It is not** —
DBOS imposes the same rule, for the same replay reason: the workflow function
must be deterministic, and all non-deterministic work (LLM calls, tool calls,
clock reads, randomness) must live inside steps.

This is therefore **not a differentiator**, and it is largely already satisfied by
**D3** ("graph nodes written as plain functions; no framework types in node
signatures") and **R8**. What it does mean is that R8 is upgraded from a
recommendation to a hard requirement — see §4.

---

## 3. E2 — Work rediscovery without Conductor

### 3.1 The fact

From `/production/workflow-recovery`, verbatim in substance:

> When self-hosting in a distributed setting without Conductor … assign each
> executor … an executor ID. Each workflow is tagged with the ID of the executor
> that started it. When an application with an executor ID restarts, it only
> recovers pending workflows assigned to that executor ID.

**Consequence:** on a Deployment with HPA, a pod OOM-killed at minute 22 leaves
its investigation `PENDING` and unrecovered until a pod bearing the same executor
ID happens to start. That is precisely the failure mode the briefing's §1 says
must not happen.

### 3.2 The design

Three parts, all using public MIT-library APIs:

**1. Stable executor identity.** Workers run as a **StatefulSet**, with
`executor_id` derived from the pod ordinal. Because E10 requires blue/green, the
ID must also carry the colour — `blue-0`, `green-0` — so that two generations can
run concurrently without colliding. A restarting pod reclaims its own in-flight
runs automatically, which handles the common case (rolling restart, single pod
crash-loop) with no custom code.

**2. Liveness heartbeat.** Each worker writes `(executor_id, app_version,
last_seen_at)` to a table **we** own, on a few-second interval. DBOS does not
expose executor liveness without Conductor, so we supply it.

**3. Reaper.** A scheduled DBOS workflow (dogfooding the engine) that periodically:

- lists `PENDING` workflows,
- joins them against the heartbeat table,
- for any whose executor's heartbeat is stale, calls `resume_workflow(id)`, which
  resumes from the last completed step.

**Version constraint (important).** DBOS only recovers workflows whose
application version matches the executor's. The reaper therefore cannot resume an
old-version workflow onto a new-version worker — it must resume it onto a live
worker **of the matching colour**. This couples E2 and E10 tightly: the reaper is
version-aware, and a colour cannot be retired while it still owns `PENDING` work.

**Safety argument.** The dangerous outcome is double execution. It is prevented
by the conjunction of: executor pinning (only one executor owns a run), our
heartbeat (we do not resume a run whose owner is alive), version matching, and
step checkpointing (a resumed run replays completed steps from checkpoints rather
than re-executing them). E6's idempotency keys are the backstop for the residual
window.

**Scale-down caveat.** Scaling a StatefulSet from 8 to 4 pods orphans runs owned
by ordinals 4–7 permanently — the heartbeat goes stale and never returns. The
reaper handles this correctly by design (stale heartbeat → resume elsewhere), but
it means **the reaper is load-bearing for normal scale-down, not just for
crashes.** It cannot be treated as a rarely-exercised safety net; it needs a test.

### 3.3 Always enqueue, never start directly

All runs are submitted via `enqueue_workflow` onto a durable queue rather than
started in-process. An *enqueued* workflow has no owning executor yet, so the
window during which E2's machinery is needed at all is confined to genuinely
in-flight runs. This also buys E8's flow control for free.

---

## 4. E3/E4/E5 — How DBOS and LangGraph compose

### 4.1 Two patterns; we need the one the blog does not show

DBOS's LangGraph material (the Feb-2025 blog post, and the maintained "Reliable
Customer Service Agent" example) demonstrates **Pattern A**: a DBOS workflow
exposed as a LangChain `@tool`, with LangGraph remaining the top-level driver and
keeping `PostgresSaver` for agent state.

**Pattern A alone does not solve our problem.** It makes individual tools
crash-proof but leaves the *run* with no work rediscovery — if the pod dies
between tool calls, the LangGraph checkpoint sits there and nothing resumes it.
It also runs two checkpointers side by side, which is exactly the
double-checkpointing hazard flagged as briefing §6.7.

DBOS's own newest and most relevant example — the **Hacker News Deep Research
Agent** — instead demonstrates **Pattern B**: the agent loop itself is the
workflow, sub-investigations are child workflows, each LLM call and tool call is
a step, `set_event` publishes status, `recv` awaits humans. Structurally this is
a one-to-one match for our planner → workers → validator fan-out.

**Decision (E3): Pattern B is the primary structure. Pattern A is retained
specifically for write actions** (open a PR, file a Jira ticket, silence an
alert), where a self-contained durable workflow with its own idempotency key is
the right unit and where D14's approval gate already forces a workflow boundary.

**Known tension, accepted deliberately:** DBOS's Pattern B examples are
framework-free Python agent loops, not LangGraph. Adopting Pattern B demotes
LangGraph from "the orchestrator" to "graph structure invoked beneath the
orchestrator." This does not contradict **D3** — LangGraph + DeepAgents remains
the agent framework — but it does mean the durable orchestration boundary sits
*above* the graph, and the graph must be written to be entered and re-entered at
step boundaries. This is R8, and it is now mandatory rather than advisory.

### 4.2 E4 — no LangGraph checkpointer

LangGraph is compiled **without** a checkpointer. DBOS step checkpoints are the
single source of execution truth. This resolves briefing §6.7 by elimination
rather than by reconciliation: there is no second state store to diverge.

Conversational state for multi-turn chat runs (D36 makes chat a first-class run)
lives in our own run-state tables, passed explicitly into the graph — consistent
with D3's "no framework types in node signatures."

**Eval impact: net positive.** Per D8a the eval sink is fed by OTel spans (D8)
and the durable event log (D30) — never by a checkpointer, which stores state
snapshots rather than trajectories. DBOS additionally provides:

- `list_workflow_steps()` — an ordered, SQL-queryable trajectory with checkpointed
  step inputs and outputs;
- `fork_workflow(id, from_step=N)` — re-run a historical incident from step *N*
  under a new prompt version, as a **new workflow ID** with history copied, so the
  original is preserved for comparison. This directly serves register §3's
  "compare prompt v1.2 vs v1.3 across 50 historical incidents," and is strictly
  better than in-place checkpointer time-travel.

The only real loss is LangGraph's interactive state introspection when debugging,
which `fork` plus step listing covers.

### 4.3 E5 — step granularity

The briefing called granularity "the crux." The rule:

| Unit | Maps to |
|---|---|
| A run (chat, dashboard workflow, or RCA — all one primitive per **D36**) | Parent workflow |
| A sub-agent / DeepAgents worker invocation | Child workflow |
| One LLM call | One step |
| One tool call via the Tool Gateway | One step |
| One write action | Child workflow (Pattern A), with its own idempotency key |

Consequences worth stating explicitly:

- **Retry waste is bounded to one LLM call** (accepted in session, Q6).
- **D33's "signal check at every tool-call boundary" is satisfied structurally**,
  not by a bespoke hook: since every tool call is a step, and cancellation
  preempts at the next step boundary, the requirement falls out of the granularity
  rule.
- Write amplification is one Postgres write per step, ~1–2 ms — accepted in
  session (Q3b), and consistent with DBOS's published >40K steps/sec benchmark
  against a single Postgres.
- **Steps must return pointers, not payloads.** Large tool artifacts go to object
  storage, with the step returning a reference — required by DBOS for write-size
  reasons, and independently required by D34, which already routes artifacts to
  object storage and fetches them on demand.

---

## 5. E6 — Idempotency

Three distinct layers, each with a different key:

| Layer | Key | Mechanism |
|---|---|---|
| **Run creation** (duplicate webhook, retried API call, double-click) | `workflow_id` set from a caller-supplied idempotency key | Enqueuing twice with the same `workflow_id` yields one run |
| **Trigger dedupe** (alert storm re-firing the same alert) | `deduplication_id` on the queue | Only one workflow with a given dedupe ID may be `ENQUEUED`/`PENDING` on a queue at a time |
| **Write side effects** (PR, Jira, silence, remediation) | `(graft_run_id, step_id, idempotency_key)` | Passed to the Tool Gateway and to the upstream API's own idempotency facility where one exists |

The third layer is the one that carries real production risk and is the reason
R8's "side-effect idempotent" clause exists. It must survive retry, reconnect,
**and** replay-after-fork.

**Fork/eval runs are structurally read-only.** `fork_workflow` deliberately
re-executes from a chosen step, so a forked run replaying an investigation would
otherwise re-file its Jira ticket or re-open its PR. Forked runs are therefore
denied write tool classes by the same capability-token mechanism as **D13** —
enforced by the token's contents, not by a policy check that could be bypassed.

---

## 6. E7/E8/E9/E11 — Cancellation, budgets, signals, timers

### 6.1 E7 — cancellation contract

- **Latency:** bounded by the current step's duration. A cancel arriving mid-way
  through a 40-second PromQL query takes effect when that query returns. Accepted
  in session (Q4). `preemptible=True` steps are **not** used in v1; they remain
  available if a latency complaint ever materialises.
- **Propagation:** `timeout_ms` / `deadline_epoch_ms` cancel the workflow **and
  all its children**, so sub-agent teardown is native rather than hand-rolled.
- **Teardown scope for v1:** child workflows (sub-agents) and pending queue
  entries. In-flight tool calls complete and are discarded. Phase-2 sandboxes
  (D4) will need explicit teardown and are out of scope here.

### 6.2 E8 — where budgets are enforced

The briefing asked whether this is orchestrator, agent, or Tool Gateway. It is
deliberately all three, at different layers:

| Control | Enforced by | Mechanism |
|---|---|---|
| Concurrent runs per workspace/tenant | **Orchestrator** | Durable queue **partition key** = workspace, with per-partition concurrency and rate limits — natively implementing **D17**'s ceiling chain |
| Per-run wall-clock ceiling | **Orchestrator** | `timeout_ms` / `deadline_epoch_ms` |
| Max graph depth (~15 steps), loop breakers (same tool + same args twice) | **Agent** | Semantic, needs graph context the orchestrator lacks |
| Per-run token/cost cap | **Agent**, reported via `budget_consumed`/`budget_warning` (D29) | Needs per-call token accounting |
| Per-connection throttles protecting *customer* infrastructure | **Tool Gateway** (D7, D17) | Keyed by connection, independent of workspace quota |

### 6.3 E9 — signal delivery supersedes D33's provisional mechanism

**D33** specified a Postgres signal table plus `LISTEN/NOTIFY`, explicitly marked
provisional pending this session. It is replaced by **DBOS `send`/`recv`**:

- `DBOS.send(workflow_id, message, topic)` — persisted, exactly-once from within a
  workflow; callable from outside the worker via `DBOSClient`, or even from
  PL/pgSQL via `dbos.send_message`.
- `DBOS.recv(topic, timeout_seconds)` — the durable multi-hour HITL wait.

D33's REST back-channel is **unchanged** — the REST handler now calls `send`
instead of inserting into our own signal table. **D30's event log is entirely
unaffected**, preserving the briefing's §7.7 requirement that streaming remain
independent of the orchestrator choice. We continue to use our own event log
rather than DBOS's `set_event`/streaming features, keeping D29/D30/D31 intact.

### 6.4 E11 — durable-timer inventory (all v1)

| # | Use case | Mechanism | Notes |
|---|---|---|---|
| **a** | HITL approval wait | `recv(topic, timeout_seconds)` | **Now bounded** — see below. Survives restarts |
| **b** | Scheduled / recurring RCA | `create_schedule` per workspace | Runtime-creatable/pausable/deletable, stored in the database — so per-workspace schedules are ordinary data, not config redeploys. **These are `system_initiated` runs and therefore structurally read-only per D13.** Must carry `tenant_id`/`graft_tenant_id` per R3 and count against D17 ceilings |
| **c** | Infra-memory refresh (`*/15`) | `apply_schedules` (static set, applied atomically at start) | Register §7 still defers the memory subsystem itself; only the timer mechanism is settled here |
| **d** | Auto-close of stale runs | Sweeper schedule + per-run expiry | **Load-bearing for E10** — see below |
| **e** | Per-run wall-clock deadline | `deadline_epoch_ms` at enqueue | Cancels the run **and all children**. Runaway protection and cancellation propagation in one field |

**The (a)+(d) interaction is the significant one.** D35 deliberately specifies
*no escalation path* for unanswered approvals — "the run simply waits for its
owner to return." Combined with E10's version pinning, an unbounded wait would
pin an old code version alive indefinitely: one forgotten approval could block
retiring a deployment colour for weeks.

**Therefore the HITL approval wait is bounded in v1.** An unanswered approval
expires via (d), closing the run as `expired` rather than escalating it — which
preserves D35's "no escalation" stance while making E10's drain window finite.
The expiry duration is a product decision not yet taken; it must exceed a
realistic on-call handover (a weekend, so ≥72h) and is the effective upper bound
on how long a deployment colour must be retained.

---

## 7. E10 — Deploy strategy and what "version" means

### 7.1 What DBOS versions actually are

An **application version** is, by default, **automatically computed from a hash of
your workflow source code**. It can be overridden explicitly via the
`application_version` config key. Every workflow is tagged with the version it
started on, and **DBOS only recovers workflows whose version matches the current
application version** — deliberately preventing a half-finished run from
resuming against code whose step sequence no longer matches its checkpoints.

So "the old version" is not a release tag we invent; it is the identity of the
code generation a run was born under.

### 7.2 Auto-hash, not git SHA

It is tempting to pin `application_version` to the git SHA or image tag. **We
should not.** Pinning to the SHA means *every* deploy creates a new version and
therefore requires a full drain, including deploys that change nothing about
workflow structure.

The default auto-computed hash changes only when **workflow source code** changes
— that is, when what steps run or in what order changes, which is precisely when
draining is necessary. A prompt-text edit inside a step, a model swap, or a
bug-fix within a step body does not alter step ordering and so does not force a
drain. Given how frequently prompts will change, this distinction is the
difference between draining on most deploys and draining on few.

**Recommendation: use the default auto-computed version**, and treat any deploy
that changes it as a structural deploy requiring blue/green.

### 7.3 Blue/green, as DBOS recommends

For versioning, DBOS explicitly recommends blue/green: launch processes on the
new version, keep processes on the old version running, direct new traffic to the
new version, and let the old drain.

Concretely for us:

1. New work is enqueued pinned to the latest version, via
   `get_latest_application_version()` + `SetEnqueueOptions(app_version=…)`.
   Scheduled workflows (E11 b, c) are automatically enqueued to the latest
   version, so they need no special handling.
2. The old colour keeps running, executing only its own in-flight runs.
3. Retirement is gated on `list_workflows(app_version=…, status=["ENQUEUED",
   "PENDING"])` returning empty — a check our deploy pipeline must perform, not a
   human eyeball.
4. E11 (d)'s approval expiry bounds how long step 3 can take.

**Patching** (`DBOS.patch()` / `deprecate_patch()`) is available as the
alternative strategy and is the better tool for an urgent fix that must reach
already-running investigations. It is not the default, because it accumulates
conditionals in workflow code. v1 default is versioning + blue/green; patching is
the documented escape hatch.

---

## 8. New risks introduced by this decision

| # | Risk | Notes |
|---|---|---|
| **X1** | **DBOS's system database falls into PCI-DSS scope.** Step inputs/outputs are checkpointed there; an unscrubbed log line could carry a PAN. | Extends **D25**. Mitigated structurally by E5's "pointers, not payloads" rule, but the scrubbing boundary must be re-examined in the Evals & Benchmarks session that already owns PAN detection. |
| **X2** | The reaper (E2) is load-bearing for routine scale-down, not just crashes — and must be version-aware. | Needs an explicit test, not an assumed-correct safety net. |
| **X3** | ~~Workflow code changes break in-flight runs.~~ **Resolved by E10.** | Residual: the deploy pipeline must gate colour retirement on a `list_workflows` check, and operators must understand that a structural change plus a long-lived approval keeps a colour alive. |
| **X4** | Pattern B demotes LangGraph below the durability boundary, and DBOS's Pattern B references are not LangGraph-based. | We are the integration point. Prototype the parent-workflow-drives-LangGraph shape early. |
| **X5** | Worker placement across GCP + AliCloud (briefing §6.9) is unaddressed. | DBOS queues can restrict which workers run which workflows, which is the likely lever, but multi-region Postgres for the system database is an open topology question for the Deployment session. |
| **X6** | **Per-workspace cron schedules (E11 b) are a new tenant-scoped resource.** | They live in the database and are runtime-mutable, so they need R3 scoping columns, D16-style versioned policy treatment, and a D17 ceiling on schedule count/frequency. Flag into `03-tenancy-and-scoping.md`. |
| **X7** | Two colours of workers run concurrently against one system database during every structural deploy. | Doubles peak worker count and Postgres connections during drains; capacity planning must assume it. |

---

## 9. Verification log (2026-09-12)

Verified live against `docs.dbos.dev` and `dbos.dev`:

- `dbos-transact-py` is **MIT**; self-hosted Conductor is **proprietary, licence-keyed**.
- Distributed recovery without Conductor is **executor-ID-pinned**.
- `cancel_workflow` preempts **at the beginning of the next step**; `preemptible`
  steps exist for immediate async interruption.
- `DBOS.sleep()` is durable; cron schedules are **stored in the database** and can
  be created, paused, resumed and deleted **at runtime**; each firing executes on
  **exactly one** worker; scheduled workflows are **automatically enqueued to the
  latest application version**.
- `send`/`recv` are persisted with exactly-once delivery from workflows.
- `fork_workflow` copies history to a **new workflow ID** and re-runs from a chosen step.
- `dbos.enqueue_workflow` exposes `workflow_id`, `deduplication_id`, `priority`,
  `timeout_ms`, `deadline_epoch_ms`, `queue_partition_key`, `delay_until_epoch_ms`,
  `authenticated_user`, `authenticated_roles`.
- `timeout_ms`/`deadline_epoch_ms` cancel **the workflow and all its children**.
- Partitioned queues apply concurrency and rate limits **per partition**.
- **Application version defaults to a hash of workflow source code**, overridable
  via `application_version`; **recovery only matches like versions**; DBOS
  recommends **blue/green** draining, with `get_latest_application_version()` and
  `list_workflows(app_version=…)` as the supporting APIs.
- **Patching** (`DBOS.patch`, `DBOS.deprecate_patch`) requires `enable_patching`
  in config and raises `DBOSUnexpectedStepError` when misused.
- Benchmark claim: **>40K workflows/steps per second** on a single Postgres.
- DBOS maintains a **LangGraph example** ("Reliable Customer Service Agent") and a
  **Pattern B** deep-research agent example; first-party *adapter packages* exist
  for Pydantic AI, LlamaIndex, OpenAI Agents SDK, Google ADK and Vercel AI —
  **LangGraph has a documented pattern, not an adapter.**
- Corroborating **D30**: DBOS published *"Postgres LISTEN/NOTIFY Can Actually
  Scale"* (Jul 2026) — 60K writes/sec at millisecond latency.

**Not yet verified — do before build:**

1. DBOS Python **async** ergonomics with async LangGraph and `langchain-mcp-adapters`.
2. Whether `resume_workflow` on a workflow whose executor is alive-but-silent can
   double-execute — the exact safety envelope of E2's reaper.
3. Behaviour of `list_workflows` filtering by executor ID without Conductor.
4. Interaction of DBOS system-database migrations with our own Postgres migrations
   and **R3**'s row-level security (DBOS tables are not RLS-aware).
5. Whether the auto-computed application version is stable across Python versions,
   dependency upgrades and container rebuilds — E10's "few drains" argument
   depends on it changing *only* on real workflow-code changes.
---

## 10. E12 — Reversibility: could we move to Temporal later?

Asked directly in review: *"Is it possible to start with DBOS and later switch to
Temporal if scaling becomes an issue?"* Short answer: **yes, and the migration is
bounded — but scaling is almost certainly the wrong trigger to watch for.**

### 10.1 Interrogating the premise: throughput will not be the binding constraint

Our published workload (briefing §1) is **tens of simultaneous runs**, bursty.
Under E5's granularity, a run emits roughly one step per LLM or tool call — call
it order-of one step per second per run at the busiest. A hundred concurrent
investigations is therefore on the order of **100 steps/sec**, against DBOS's
published **>40K workflows-or-steps/sec on a single Postgres**. That is roughly
**two to three orders of magnitude of headroom**.

Long before the orchestrator saturates, the binding constraints will be:

1. **LLM/GPU capacity** (LiteLLM/vLLM throughput, provider rate limits),
2. **Tool-call limits against customer infrastructure** — the shared K8s control
   plane that D17's per-connection throttles exist to protect,
3. **Postgres connection count**, not Postgres throughput — aggravated by X7's
   blue/green doubling, and the one thing D30 already names as its revisit trigger
   (`LISTEN/NOTIFY` connection scaling).

**Temporal would not help with any of the three.** (3) is mitigated by a pooler
such as PgBouncer; (1) and (2) are the agent's and the Tool Gateway's problem.

And if raw orchestration throughput *did* ever bind, DBOS's own answer is to
**shard workflows across multiple Postgres databases** — for which R3's
`tenant_id`/`graft_tenant_id` is a natural shard key. That is a materially cheaper
escape than changing engines.

### 10.2 The realistic reasons to revisit — none of them are throughput

| Trigger | Assessment |
|---|---|
| **Multi-cloud active-active (GCP + AliCloud), briefing §6.9 / X5** | The genuinely hard one. A single system database is a poor fit for active-active across clouds. **But Temporal has the same problem** — its cluster needs a co-located datastore too. The likely answer either way is **one application + one system database per region, with runs pinned to a region**, not a globally shared orchestrator. |
| **Operational maturity / hiring** | Temporal is the better-known quantity with a deeper operational corpus. A legitimate reason; unrelated to scale. |
| **Postgres connection pressure** | Mitigate with a pooler first. Only an engine question if pooling fails. |
| **DBOS project health** | A young company; the library is MIT and self-hostable, which caps the downside, but it is worth periodic review. |

### 10.3 What a migration would actually cost

The briefing's core worry was that the *irreversible* part is graph
decomposition, not engine choice. **That worry is fully discharged:** E5/D41's
granularity rule — run = workflow, sub-agent = child workflow, LLM call = step,
tool call = step — is engine-agnostic and maps one-to-one onto Temporal's
workflow / child-workflow / activity model. That is exactly what R8 asked for, and
it is satisfied whichever engine we run.

Mapping the rest:

| Ours | Temporal equivalent | Cost |
|---|---|---|
| E9 `send`/`recv` | Signals | ≈ 1:1 |
| E11 durable sleep, cron schedules | Timers, Schedules | ≈ 1:1 |
| E6 `workflow_id` / `deduplication_id` | Workflow ID + reuse policy | ≈ 1:1 |
| E7 deadlines cancelling children | Workflow timeouts + cancellation scopes | ≈ 1:1 |
| **E2 heartbeat + reaper** | **Deleted entirely** — native cluster-side | **Negative cost: we delete code** |
| E10 blue/green version pinning | Worker versioning / build IDs | Conceptually similar, mechanically different |
| **E8 per-partition queue flow control** | **No direct equivalent** — DBOS's own comparison notes Temporal lacks comparable queueing/flow-control abstractions | **Real rework.** D44's per-workspace concurrency/rate limits (D17's ceiling chain) would need reimplementing |
| **E4 `fork_workflow` for evals** | Reset is roughly analogous but not identical | **Partial rework** of the prompt-comparison eval flow |

So a migration is **moderate, bounded and mostly mechanical**, with exactly two
areas of genuine rework: per-workspace flow control, and the fork-based eval loop.
Both are areas where DBOS is *better* than Temporal for us — which is a further
argument that migration pressure is unlikely to come from capability.

### 10.4 DBOSify as a hedge — considered and rejected

**DBOSify** (`pip install dbosify`) is a drop-in replacement for the **Temporal
Python SDK** backed by Postgres via DBOS Transact: you `import dbosify` instead of
`temporalio`, and point clients and workers at a connection string instead of a
Temporal server. It supports workflows, activities, signals, updates, queries,
retries and recovery.

It is marketed for Temporal → DBOS, but it structurally enables the reverse hedge:
**write against the Temporal SDK API now, run it on Postgres, and "switch to
Temporal" later by changing imports and pointing at a server.**

**Rejected, for three reasons:**

1. **It forces a lowest-common-denominator design.** Writing to the Temporal API
   surface forfeits precisely the DBOS-native features this design is built on —
   `queue_partition_key` flow control (E8/D44), `fork_workflow` (E4/D40),
   `deduplication_id` (E6), runtime-mutable database-stored schedules (E11), and
   `list_workflow_steps` trajectories. We would pay the migration cost *up front,
   permanently*, to insure against an event §10.1 shows is unlikely.
2. **It is a young, Python-only compatibility layer** in the critical path of the
   least-reversible component in the system, with partial feature compatibility
   documented in its own `ARCHITECTURE.md`.
3. **It insures the wrong risk.** §10.2 shows the plausible trigger is topology
   (multi-cloud), which DBOSify does nothing for.

### 10.5 What we do instead: a thin `runtime` seam

Not a `RunController` driver port — that idea (R8's original framing) is
unworkable in practice, because DBOS's value comes from decorators applied to our
own functions, and determinism constraints cannot be hidden behind an interface.
A wrapper pretending otherwise would be leaky and would buy little.

Instead, a **single small internal module** through which all engine interaction
flows, so that domain and agent code never imports `dbos` directly:

- `enqueue_run(...)` → `enqueue_workflow` with workflow ID, dedupe ID, partition
  key, deadline
- `await_human(graft_run_id, timeout)` → `recv`
- `signal(graft_run_id, message)` → `send`
- `sleep_until(...)` → `DBOS.sleep`
- `cancel(graft_run_id)`, `resume(graft_run_id)`, `fork(graft_run_id, step)`
- `list_runs(...)`, `list_steps(graft_run_id)`

This is worth doing **regardless of migration**: it is the natural chokepoint for
D15 audit emission, D29 event publication, R3 tenant scoping and D17 ceiling
checks, and it makes the engine testable by substitution. It is hygiene that
happens to also cap migration cost — not an abstraction built on speculation.

**It does not, and is not meant to, make the engine swappable by configuration.**
The `@DBOS.workflow()` / `@DBOS.step()` decorators stay on our functions. Swapping
engines means re-decorating and rewriting §10.3's two rework areas. That is the
honest, bounded cost, accepted.

