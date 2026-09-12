# Open Question 02 — Streaming, Event Model & Surface Delivery

> **Purpose of this document.** Self-contained briefing for a dedicated deep-dive
> session. Nothing here is decided.
>
> Source research: `docs/research/streaming.md`, `docs/research/auth.md` §3,
> `docs/research/session.md`.
> Related: `04-durable-execution.md` (run lifecycle), `03-tenancy-and-scoping.md`
> (who may subscribe to a stream).

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

| Surface | Transport reality |
|---|---|
| Custom web frontend | Full control. SSE or WebSocket both viable. |
| **Grafana App Plugin** | Go plugin backend. Either proxy a stream through it, or use **Grafana Live** (Grafana's own WebSocket infra) via the backend plugin `StreamHandler` (`SubscribeStream` / `RunStream` / `PublishStream`). |
| **Slack** | Not a stream. Message post + update, or (per research doc) Slack's 2026 streaming APIs (`chat.startStream` / `appendStream` / `stopStream`). Must be batched/throttled either way. |
| Direct API consumers | Expect an LLM-provider-shaped SSE endpoint: `GET /runs/{id}/stream`. |

---

## 2. Decisions already locked (constraints)

- **D6** Streaming is **decoupled from orchestration** via a durable event log.
  One internal event model; surfaces are thin adapters. Consequence: the
  orchestrator choice (see `04-durable-execution.md`) does **not** affect
  streaming.
- **D1** Grafana traffic goes through the plugin backend, not browser → API.
- **R4** (pending) Investigations are **workspace-owned**, not user-owned — which
  makes multi-viewer fan-out a product requirement rather than a bonus.

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

## 4. Open questions

### B1 — Event schema: adopt AG-UI, or define our own?

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

### B2 — Durable log substrate

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

### B3 — Grafana delivery: Grafana Live vs SSE through the plugin proxy

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

### B4 — Multi-viewer / shared live investigations in v1?

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

### B5 — Back-channel transport (cancel, steer, approve, follow-up)

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

### B6 — Streaming granularity per surface

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

### B7 — Run lifecycle when no one is watching

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

## 6. What a good outcome looks like

1. A decided event taxonomy and schema-ownership stance (B1).
2. A chosen log substrate with retention and archival policy (B2).
3. A Grafana delivery mechanism (B3) with verified constraints.
4. A multi-viewer interaction model, including steering conflicts (B4).
5. A back-channel design with idempotency and signal-delivery mechanics (B5).
6. A per-surface granularity matrix (B6).
7. A notification design for unattended runs and blocked approvals (B7).

---

## 7. Things to verify before deciding (do not assume)

- Grafana Live: message size limits, throughput, auth model for channels,
  availability across Grafana OSS / Enterprise / Cloud.
- Slack streaming APIs asserted in `streaming.md` (`chat.startStream` etc.) —
  confirm they exist, their rate limits, and SDK support, before designing around
  them. Have a `chat.update`-batching fallback either way.
- AG-UI protocol maturity, stability, and actual LangGraph integration quality.
- Redis Streams behaviour under consumer-group failure and trimming during an
  active reconnect.
