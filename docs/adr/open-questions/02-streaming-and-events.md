# Open Question 02 — Streaming, Event Model & Surface Delivery

> **Status: 🟢 Fully resolved for v1 (2026-09-12).** The original briefing
> (§1–§7 below) is preserved as the historical record. **§0 summarises the
> resolutions** — locked as **D29–D36** in
> [`../DECISION-REGISTER.md`](../DECISION-REGISTER.md) — reached in an
> interview session that also live-verified Grafana's own Grafana Live
> documentation and reviewed a sibling project (`vikshana-graft-app`) as
> comparative evidence. Nothing in this track blocks moving on; remaining
> items are implementation-time verification spikes, not open architectural
> questions.

---

## 0. Resolution summary

### 0.1 What changed the shape of this question

Two things emerged during the interview that weren't anticipated in the
original briefing:

- **"Chat" and "RCA investigation" turned out to be the same architectural
  primitive.** The original briefing implicitly assumed RCA-style long runs
  were the hard case and quick chat Q&A would need a lighter path. That
  turned out to be wrong: chat here also triggers multi-minute workflows
  (building dashboards, creating alerts), needs the same tool-call
  verification/approval gates, needs end-to-end audit, and needs to be
  resumable later — i.e. it needs everything a durable run needs. A draft
  two-tier split (lightweight/undurable chat vs. heavy/durable RCA runs) was
  proposed, tested against these requirements, and **rejected** in favour of
  one unified "run" model for every agent interaction. See **D36**.
- **Two pieces of comparative evidence, both confirming the same thing —
  differently:**
  - `vikshana-graft-app` ("Graft"), a materially simpler existing Grafana
    AI-assistant plugin, was inspected directly (source on GitHub). It runs
    **entirely client-side** — no Grafana Live, no SSE, no durable backend
    event log, chat history in `localStorage`, non-streaming
    `llm.chatCompletions()` calls with a browser-side agent loop. This works
    *because* its use case has none of our requirements (no audit, no
    resumability guarantee, no tool-approval gates, personal/ephemeral
    sessions). It is evidence for *why* the full architecture below is
    needed here, not a template to copy.
  - Grafana's own **Grafana Assistant** product documentation independently
    confirms the same "chat vs. investigation" split exists at Grafana Labs
    too — their on-prem/OSS tier explicitly excludes "Assistant
    investigations and related investigation memory features," which stay
    Cloud-backend-only. Useful confirmation that this is a real, recognised
    fork in this problem space — we've just resolved it differently (one
    unified backend for both, D36) given our stricter audit/persistence
    requirements even for plain chat.

### 0.2 Resolutions, per original question

| # | Question | Resolution | Decision |
|---|---|---|---|
| **B1** | Event schema: AG-UI or own? | **Own internal model**, versioned (`event_version`), additive-only. AG-UI is at most a future adapter for the custom web frontend — never Grafana (no natural bridge between AG-UI's SSE/React client and Grafana Live's channel/DataFrame model, verified by reasoning about both architectures) or Slack. Taxonomy extended with `plan_updated`, `budget_consumed` (distinct from `budget_warning`), `sub_agent_spawned`. | **D29** |
| **B2** | Durable log substrate | **Postgres-only — no Redis.** One event table, `LISTEN/NOTIFY` fan-out, indexed replay. Rejected the initially-proposed Redis-Streams-hot + Postgres-archive split: Postgres alone gives transactional consistency with run state and needs no trimming/retention/fallback design at expected scale. | **D30** |
| **B3** | Grafana delivery: Live vs SSE-through-proxy | **Grafana Live**, confirmed via live verification of Grafana's own docs. `@grafana/ui` frontend, no AG-UI. **OSS self-hosted is the primary deployment target** — Grafana Live's HA/Redis requirement (`ha_engine`) only bites customers running multiple Grafana instances behind a load balancer, not the common single-instance OSS case; `max_connections` default of 100 must be raised by the customer admin (install-doc callout). Message-size/throughput limits are undocumented — flagged as a pre-build verification spike. | **D31** |
| **B4** | Multi-viewer in v1? | **Yes — soft-lock "driver" model** (screen-share analogy). New viewers join live from "now" with an explicit scroll-back action. **Only activates when a run is explicitly shared** — see D36. | **D32** |
| **B5** | Back-channel transport | **Plain REST**, idempotency-keyed (locks R7). Signal delivery: **Postgres signal table + `LISTEN/NOTIFY`**, reusing B2's substrate — explicitly provisional pending `04-durable-execution.md`. Cancel/signal checked **at every tool-call boundary**. | **D33** |
| **B6** | Streaming granularity per surface | **Token-level narrative on all surfaces, including Grafana Live** (deliberately overriding an initial "coarser for Grafana" instinct, given chat is now a frequent interaction per D36). Step-level for everything else except Slack (always batched). Raw tool output never streamed — on-demand `GET /runs/{id}/events/{event_id}/artifact`, rendered per type, with a **diff view** specifically for proposed dashboard/alert changes. | **D34** |
| **B7** | Run lifecycle when unwatched | Slack bot posts a completion summary; Grafana/web surface an in-app badge/inbox. **No escalation** for unanswered `hitl_required` in v1. | **D35** |
| *(new)* | Chat vs. investigation architecture | **Same "run" primitive for both** — one event log, one audit trail, one tool-approval mechanism. **User-owned by default, promotable to workspace-shared** (activates D32). Refines R4 (see `open-questions/03-tenancy-and-scoping.md`). | **D36** |

### 0.3 Verified facts (Grafana Live, live-checked 2026-09-12 against Grafana's own docs)

These replace several "verify, don't assume" items from the original §7:

- Grafana Live is **enabled by default**, WebSocket-based, Pub/Sub, channel
  format `scope/namespace/path` (max 160 chars).
- Default **`max_connections = 100`** per Grafana server instance — one
  WebSocket connection per browser tab, multiplexing all channel
  subscriptions. Must be raised for any real team size; not something we
  control from the plugin.
- Default in-memory pub/sub is **single-instance-scoped**. Multi-instance
  Grafana deployments (behind a load balancer) require Grafana's own
  `ha_engine = redis` config to fan out correctly across instances — this is
  a **customer Grafana-infra prerequisite**, not our system's Redis (which
  we explicitly decided against, D30). Not a default concern for OSS
  self-hosted single-instance deployments, which we're targeting primarily.
- **No documented per-message size limit.** Data must be JSON-encoded over
  WebSocket channels. Treated as a verification spike, not an assumption.
- Channel authorization: enforced in our own `SubscribeStream` handler using
  the plugin context's authenticated user/org — architecturally confirmed,
  exact request/context shape still to confirm against the plugin SDK at
  implementation time.

### 0.4 Remaining action items (implementation-time, not open questions)

- Prototype the largest expected event payload through a Grafana Live test
  channel to establish real size/throughput limits (D31).
- Confirm the exact `SubscribeStream` request/context shape against the
  Grafana plugin SDK (D31).
- Design the driver-disconnect fallback for D32's soft-lock (auto-release
  timeout vs. explicit hand-off requirement) — not yet decided, just flagged.
- Confirm exact Grafana Live channel-naming convention for app plugins
  (`plugin/<id>/run/<run_id>` proposed, the verified example was for
  `ds`-scope data source plugins specifically).
- `open-questions/03-tenancy-and-scoping.md` should reconcile R4 against
  D36's refined ownership model when that session runs.
- `open-questions/04-durable-execution.md` inherits two constraints from
  D33: a signal-check hook at every tool-call boundary, and a provisional
  Postgres-table signal mechanism to confirm or replace depending on
  orchestrator choice.

---

## 1. System context

An SRE agent run is **long** and **multi-step**. A chat answer may take seconds;
an RCA run takes 30–90 seconds in the simple case and **up to ~30 minutes** for
multi-agent deep investigations, plus potentially **multi-hour human-in-the-loop
pauses** awaiting approval.

For this product the *process* is as valuable as the answer: users want to watch
evidence being gathered, hypotheses forming and being discarded, and which tools
ran with what inputs. "Thinking out loud" is a feature, not debug output.

Output must reach **three human surfaces** with very different transport
characteristics:

| Surface                | Transport reality                                                                                                                                                                                        |
|------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Custom web frontend    | Full control. SSE or WebSocket both viable.                                                                                                                                                              |
| **Grafana App Plugin** | Go plugin backend. Either proxy a stream through it, or use **Grafana Live** (Grafana's own WebSocket infra) via the backend plugin `StreamHandler` (`SubscribeStream` / `RunStream` / `PublishStream`). |
| **Slack**              | Not a stream. Message post + update, or (per research doc) Slack's 2026 streaming APIs (`chat.startStream` / `appendStream` / `stopStream`). Must be batched/throttled either way.                       |
| Direct API consumers   | Expect an LLM-provider-shaped SSE endpoint: `GET /runs/{id}/stream`.                                                                                                                                     |

---

## 2. Decisions already locked (constraints)

- **D6** Streaming is **decoupled from orchestration** via a durable event log.
  One internal event model; surfaces are thin adapters. Consequence: the
  orchestrator choice (see `04-durable-execution.md`) does **not** affect
  streaming.
- **D1** Grafana traffic goes through the plugin backend, not browser → API.
- **R4** (pending) Investigations are **workspace-owned**, not user-owned — which
  makes multi-viewer fan-out a product requirement rather than a bonus.
  **Refined by D36** — see §0.2.

---

## 3. The core architecture (agreed in principle)

```
LangGraph / DeepAgents worker
        │ publishes typed events (run_id, monotonic event_id)
        ▼
   Durable event log            ◀── the single source of truth
        │
        ├──▶ SSE adapter          → custom frontend, direct API consumers
        ├──▶ Grafana Live adapter → Grafana App Plugin
        └──▶ Slack adapter        → batched/throttled message updates
```

Back-channel (cancel, steer, approve) is a **separate path** — see B5.

---

## 4. Open questions *(historical — see §0 for resolutions)*

### B1 — Event schema: adopt AG-UI, or define our own? *(resolved — D29, §0.2)*

`AG-UI` (Agent–User Interaction Protocol) appears in the capability braindump. It
standardises agent↔UI event streams and has LangGraph integration plus React
components.

| Option | Pros | Cons |
|---|---|---|
| **Adopt AG-UI as the internal model** | Head start on the custom frontend; third-party interop; someone else maintains the spec | Young spec; its vocabulary is generic-agent-shaped, not SRE-shaped; Grafana and Slack adapters are still custom work; coupling our core model to an external spec's evolution |
| **Own internal model, AG-UI as an *output adapter*** | Domain events we actually need (`hypothesis_updated`, `evidence_added`, `confidence_changed`, `action_proposed`, `blast_radius_computed`); spec churn is contained in one adapter | We maintain the model; slightly more work up front |

*Current leaning:* own model + AG-UI as one more adapter, consistent with the
"one internal model, thin adapters" principle already locked in D6.

Candidate event taxonomy to critique:
`token` · `agent_thought` · `tool_call_start` · `tool_call_result` · `status` ·
`evidence_added` · `hypothesis_updated` · `confidence_changed` ·
`action_proposed` · `action_confirmed` · `action_executed` · `hitl_required` ·
`budget_warning` · `error` · `done`

**To resolve:** pick one; if AG-UI is an adapter, confirm we're not
accidentally reinventing it badly. Evaluate AG-UI's current maturity (**verify —
do not assume from the braindump**).

---

### B2 — Durable log substrate *(resolved — D30, §0.2)*

Requirements: monotonic `event_id` per run; reconnect/replay from
`Last-Event-ID`; multi-consumer fan-out; survives worker crash; retained long
enough to reconstruct an investigation; audit-grade permanence for
action-related events.

| Option | Pros | Cons |
|---|---|---|
| **Redis Streams** | Native fan-out, consumer groups, `XRANGE` replay, `MAXLEN` trimming; already in the stack for cache | Not permanent; memory-bound; trimming loses history |
| **Postgres table** | Permanent; transactional with run state; already in the stack | Fan-out means polling or `LISTEN/NOTIFY` (payload-size limited); write amplification at token granularity |
| **Kafka / Redpanda** | Durable, high-throughput, replayable, natural multi-consumer | Heavy operational dependency; overkill at expected volume |

*Current leaning:* **Redis Streams for the hot path** (live fan-out + reconnect,
`MAXLEN`-trimmed) **plus asynchronous archival** of the same events to
Postgres/object storage for permanent replay and audit. Two stores, one writer,
clear separation between "live" and "of record".

**To resolve:** hot-log retention window (24h? 7d?); whether token-level deltas
are archived or only step-level events (volume differs by orders of magnitude);
whether the archive is the same events or a compacted transcript; interaction
with WORM audit requirements from `01-identity-and-access.md` A6.

---

### B3 — Grafana delivery: Grafana Live vs SSE through the plugin proxy *(resolved — D31, §0.2/§0.3)*

| Option | Pros | Cons |
|---|---|---|
| **Grafana Live** (`StreamHandler`) | Uses Grafana's existing WebSocket infra; inherits Grafana's channel-level authz; no proxy-buffering problems; designed for exactly this | Must implement Go `StreamHandler`; message-size constraints (**verify limits**); a second delivery path to maintain; channel naming/scoping design needed |
| **SSE through the Go plugin backend** | One delivery mechanism shared with the web frontend | Go reverse-proxying SSE buffers unless written very carefully; 30-minute streams through a proxy + corporate load balancers is a known source of pain; keep-alive tuning across two hops |

*Current leaning:* **Grafana Live.** Fighting SSE buffering through a plugin
proxy for a 30-minute stream is a losing battle, and the adapter stays small
because the durable log is the real source of truth.

**To resolve:** Grafana Live message size / throughput limits; how channel scoping
maps to workspace + visibility rules; behaviour on Grafana panel reload and
dashboard navigation; whether Grafana Live is available in all deployment modes
customers use (**verify, incl. Grafana Cloud**).

---

### B4 — Multi-viewer / shared live investigations in v1? *(resolved — D32, §0.2)*

Follows from investigations being workspace-owned. Two engineers on the same
incident — one in Grafana, one in the web UI, one watching in Slack — should see
the same run.

*Current leaning:* **yes, v1.** It's nearly free once the event log is durable
and workspace-scoped, and it's a core incident-response workflow. The hard part
isn't fan-out, it's the *interaction* model.

**To resolve:** what happens when two viewers both try to steer the agent
mid-run? Options: last-write-wins; soft lock ("Alice is driving"); queue
interventions as messages. Also: does a second viewer see full history replayed,
or join live from now?

---

### B5 — Back-channel transport (cancel, steer, approve, follow-up) *(resolved — D33, §0.2)*

SSE is one-way. The braindump lists "Agent Steering" and "Split Conversation" as
capabilities, so mid-run interaction is in scope.

| Option | Pros | Cons |
|---|---|---|
| **Plain REST** (`POST /runs/{id}/cancel`, `/signal`, `/approve`) | Idempotency keys for free; identical from UI, Grafana and Slack; trivially auditable; SSE stays simple | Extra round trip; needs a signal delivery path to the running worker |
| **WebSocket both ways** | One connection | Doesn't help Grafana (Live is its own thing) or Slack at all; harder auth; harder idempotency |

*Current leaning:* **REST.** Note `streaming.md` calls out idempotency as the
issue that actually matters here — "restart the pod" must not fire twice because
a transport retried. Actions keyed by an idempotency token tied to the run, never
re-triggered by transport-layer retries.

**To resolve:** how a signal reaches an in-flight worker (this couples to
`04-durable-execution.md` — Temporal signals vs a Postgres signal table polled by
the worker); latency expectation for cancel (must a 30-min run stop within
seconds?); what "cancel" must tear down (sub-agents, in-flight tool calls,
Phase-2 sandboxes).

---

### B6 — Streaming granularity per surface *(resolved — D34, §0.2)*

*Current leaning:* token-level streaming for the **final narrative only**;
step/event-level for everything else. Slack is batched/throttled regardless.
Grafana Live may warrant coarser granularity than the web UI.

Related, from `streaming.md`: **never stream raw tool output verbatim.** A log
dump or full metric series must be summarised/truncated in the stream, with the
client fetching full detail on demand. This dovetails with the context-management
strategy (result reduction happens in the Tool Gateway) — the same reduced
artefact should feed both the LLM context and the UI.

**To resolve:** confirm per-surface granularity matrix; define the
"fetch full detail" endpoint and where the full artefact is stored.

---

### B7 — Run lifecycle when no one is watching *(resolved — D35, §0.2)*

A run is a **job, not a connection** — it continues when all viewers disconnect.
That implies a completion-notification path.

**To resolve:** which notification surface(s) for v1 — Slack DM, Grafana
annotation/alert, email, in-app inbox? Also: notification on `hitl_required`
(the run is *blocked* on a human and nobody is looking — this is the case that
actually matters), and escalation if an approval goes unanswered.

---

## 5. Reliability requirements (from `streaming.md`, treat as acceptance criteria)

- **Reconnect/resume** — browser refresh, Grafana panel reload, or a flaky Slack
  socket must not lose the run; replay from the durable log via last seen
  `event_id`.
- **Keep-alives** — long-lived connections are killed by idle load balancers and
  corporate proxies; periodic ping/comment frames required.
- **Backpressure** — stream summarised deltas, not raw payloads.
- **Idempotency** — actions keyed to the run, immune to transport retries.
- **Stream-level authorisation** — every subscription checked against the
  canonical identity and workspace scope. A Grafana Live channel or Slack thread
  must never leak another workspace's investigation.

---

## 6. What a good outcome looks like *(met — see §0)*

1. A decided event taxonomy and schema-ownership stance (B1). ✅
2. A chosen log substrate with retention and archival policy (B2). ✅
3. A Grafana delivery mechanism (B3) with verified constraints. ✅
4. A multi-viewer interaction model, including steering conflicts (B4). ✅
5. A back-channel design with idempotency and signal-delivery mechanics (B5). ✅
6. A per-surface granularity matrix (B6). ✅
7. A notification design for unattended runs and blocked approvals (B7). ✅

---

## 7. Things to verify before deciding — status, see §0.3/§0.4 for the current list

Superseded by §0.3 (live-verified) and §0.4 (remaining implementation-time
items). Kept briefly here for continuity with the original briefing:

- Grafana Live: message size limits, throughput, auth model for channels,
  availability across Grafana OSS / Enterprise / Cloud. **Partially verified
  (§0.3)** — auth model and single-instance default confirmed; message-size
  limit remains an implementation-time spike; OSS self-hosted confirmed as the
  primary target (not Cloud/Enterprise) so cross-mode availability is
  deprioritised.
- Slack streaming APIs asserted in `streaming.md` (`chat.startStream` etc.) —
  confirm they exist, their rate limits, and SDK support, before designing around
  them. Have a `chat.update`-batching fallback either way. **Still open** —
  not addressed in this session; Slack remains batched-only regardless (D34),
  so this only affects *how* batching is implemented, not whether it's needed.
- AG-UI protocol maturity, stability, and actual LangGraph integration quality.
  **Still open** — moot for v1 since AG-UI has no role outside a possible
  future web-frontend adapter (D29).
- Redis Streams behaviour under consumer-group failure and trimming during an
  active reconnect. **Moot** — Redis Streams rejected for our event log (D30).
