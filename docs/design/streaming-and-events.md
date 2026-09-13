# Streaming and the event model

> **Status: 🟢 Resolved for v1.** Mechanism for **ADR-0006**, **ADR-0029**–
> **ADR-0035**, **ADR-0064**, **ADR-0066**, **ADR-0072**.
>
> Vocabulary per [`../GLOSSARY.md`](../GLOSSARY.md). Related:
> [`durable-execution.md`](./durable-execution.md),
> [`tenancy-and-scoping.md`](./tenancy-and-scoping.md).
>
> *Created during the 2026-09-13 ADR migration: this material previously existed
> only inside register cells ADR-0029–ADR-0035, which is why those cells were the largest
> in the file.*

---

## 1. Principle

Streaming is **decoupled from orchestration** by a durable event log
(ADR-0006). The orchestrator writes events; surfaces read them. No surface ever
talks to the graph, and swapping the durable-execution engine (ADR-0048) does
not touch the streaming path.

## 2. Event model

Ours, internally owned and versioned (ADR-0029). Every event carries
`event_version`; evolution is **additive-only**; adapters must ignore unknown
event types gracefully.

**v1 taxonomy** — this list grows, which is why it lives here and not in the ADR:

`token` · `agent_thought` · `plan_updated` · `tool_call_start` ·
`tool_call_result` · `status` · `evidence_added` · `hypothesis_updated` ·
`confidence_changed` · `action_proposed` · `action_confirmed` ·
`action_executed` · `sub_agent_spawned` · `hitl_required` · `budget_consumed` ·
`budget_warning` · `error` · `done`

**AG-UI is, at most, a future output adapter for the post-v1 web frontend
only** — never for Grafana (its React/SSE-shaped client has no natural bridge to
Grafana Live's channel/DataFrame model) and never for Slack.

## 3. Substrate

Postgres only, no Redis (ADR-0030).

| Column | Purpose |
|---|---|
| `graft_run_id` | Scope |
| `graft_event_id` | Monotonic ordering and replay cursor |
| `event_type`, `event_version` | Taxonomy (§2) |
| `payload JSONB` | Event body — **pointers, never large artifacts** |
| `created_at` | |

- **Fan-out** via `LISTEN/NOTIFY`. The payload carries `graft_run_id:graft_event_id`
  only and the listener re-reads the row — this avoids the 8 KB NOTIFY ceiling.
- **Replay** via an indexed range query on `graft_event_id`.
- **Large raw tool artifacts live in object storage**, referenced by the payload,
  never inlined (ADR-0034, ADR-0041).

Chosen over a Redis-Streams-hot + Postgres-archive split because Postgres alone
gives transactional consistency with run state (single writer, no dual-write
risk) and needs no trimming, retention or hot/cold fallback design at our scale.
Revisit only if real `LISTEN/NOTIFY` connection-scaling limits are hit.

## 4. Surface adapters

| Surface | Transport | Granularity |
|---|---|---|
| Grafana plugin | **Grafana Live** `StreamHandler` (`SubscribeStream` / `RunStream` / `PublishStream`) — ADR-0031 | Token-level (ADR-0034) |
| Slack | Bot messages | **Always batched/throttled**, regardless |
| Web frontend (post-v1) | SSE | Token-level |

Grafana Live rather than SSE through the plugin's Go proxy, to avoid known
Go-reverse-proxy SSE-buffering problems on long-lived streams. Frontend uses
`@grafana/ui` directly.

**Channel authorization** is enforced inside our backend's `SubscribeStream`
handler, against the caller's plugin-context identity and Tenant/run ownership.

### 4.1 Grafana Live operational notes

- Default pub/sub is **in-memory and single-instance-scoped**. Grafana's Redis
  `ha_engine` is required only if a customer scales to multiple Grafana instances
  behind a load balancer — an edge case for OSS self-hosted, not the default.
- **`max_connections = 100` per instance must be raised by the customer admin** —
  an explicit install-doc callout, since one WebSocket is consumed per browser tab.
- **Per-message size and throughput limits are undocumented by Grafana.**
  Pre-build verification spike: prototype the largest expected event payload
  through a test channel. More important now that ADR-0034 pushes token-level
  streaming through Grafana Live.

## 5. Result rendering

Raw tool output is never streamed verbatim (ADR-0034). Inline content is
truncated/summarised by Tool Gateway result reduction; the untruncated artifact
is fetched on demand:

```
GET /runs/{graft_run_id}/events/{graft_event_id}/artifact
```

Rendered per content type: log viewer, JSON viewer, and specifically a **diff
view** for proposed dashboard and alert-rule changes, so an approver can evaluate
an `action_proposed` event before confirming.

## 6. Back-channel

Plain REST, idempotency-keyed to the run, identical across Grafana, Slack and
the post-v1 web frontend (ADR-0033): `cancel`, `signal`, `approve`,
`request-control`, `release-control`.

**Signal delivery is DBOS `send`/`recv`** (ADR-0045) — the REST handler calls
`send` rather than inserting into a bespoke signal table. The event log is
unaffected. Cancel is checked at every step boundary, which ADR-0041 satisfies
structurally.

## 7. Multi-viewer and control

Only relevant once a run is promoted to Tenant-shared (ADR-0054) — a private run
has no multi-viewer concern by construction.

- **One driver, everyone else watches, handover is explicit** (ADR-0032,
  ADR-0064). `viewer` can never drive (no `run:steer` verb, ADR-0056).
- **Control is approval authority** (ADR-0065) — every transfer of control is a
  transfer of approval authority and is audited as such.
- **Three independent server-side clocks** (ADR-0066): idle (10 min, reset by
  interactive acts only), disconnect (2 min, `SubscribeStream` teardown), and
  approval (≥72 h, never reset). Evaluated by a 30-second scheduled sweep, not a
  per-run durable timer. Slack has no transport liveness, so a Slack driver has
  only the idle clock.
- New viewers see the **live tail by default**, with explicit scroll-back backed
  by §3's replay query.

## 8. Notification

Slack bot posts a completion summary; Grafana and the web frontend surface an
in-app badge/inbox (ADR-0035). Unanswered `hitl_required` approvals **expire**
rather than waiting indefinitely (ADR-0047), which keeps ADR-0046's blue/green
drain window finite.

## 9. Run list

Filters are **"Mine"** and **"Tenant"** only (ADR-0072) — there is no "my team"
(Group is not a scoping layer, ADR-0051) and no "all" (cross-Tenant listing does
not exist).
