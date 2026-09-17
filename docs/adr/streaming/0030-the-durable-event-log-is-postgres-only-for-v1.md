---
id: ADR-0030
title: The durable event log is Postgres-only for v1
status: accepted
date: 2026-09-12
deciders: [ ]
category: streaming
tags: [ streaming, events ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/streaming-and-events.md
legacy_id: D30
---

# ADR-0030 — The durable event log is Postgres-only for v1

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D30`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

The durable event log (ADR-0006) needed a storage substrate. A Redis-Streams-hot + Postgres-archive split was initially
proposed, which would require trimming/retention/hot-cold-fallback design; a Postgres-only design instead needed
evaluating for whether it could satisfy fan-out (`LISTEN/NOTIFY`'s ~8KB payload ceiling) and replay requirements without
that additional complexity.

## 2. Decision

**Durable event log is Postgres-only for v1 — no Redis.** One event table (`graft_run_id`, monotonic `graft_event_id`,
`event_type`, `event_version`,
`payload JSONB`, `created_at`); fan-out via `LISTEN/NOTIFY` (payload carries `graft_run_id:graft_event_id`, listener
re-reads the row — avoids the 8KB NOTIFY size ceiling); replay via an indexed range query on
`graft_event_id`. Chosen over the initially-proposed Redis-Streams-hot + Postgres-archive split because Postgres alone
gives transactional consistency with run state (single writer, no dual-write risk) and needs no
trimming/retention/hot-cold-fallback design at our expected scale. Large raw tool artifacts live in object storage,
referenced by event payload, never inlined. Revisit only if real `LISTEN/NOTIFY`
connection-scaling or event-rate limits are hit in production.

## 3. Considered options

| Option                                                                                             | Verdict     | Why                                                                                                                                                                            |
|----------------------------------------------------------------------------------------------------|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Redis-Streams-hot + Postgres-archive split                                                         | ❌ Rejected | Requires trimming/retention/hot-cold-fallback design and introduces a dual-write risk between Redis and Postgres for run state consistency.                                    |
| Postgres-only event table, `LISTEN/NOTIFY` fan-out (payload carries a pointer, not the event body) | ✅ Chosen   | Transactionally consistent with run state (single writer); no trimming/retention design needed at expected scale; the pointer-payload trick avoids NOTIFY's ~8KB size ceiling. |

## 4. Consequences

- **Positive —** transactional consistency between the event log and run state, with no dual-write risk between two
  different stores.
- **Negative / accepted trade —** large raw tool artifacts cannot be inlined in the event payload — they must live in
  object storage and be referenced by pointer.
- **Follow-on work —** listeners must re-read the row rather than trusting the NOTIFY payload to carry the full event
  body.
- **Revisit trigger —** real `LISTEN/NOTIFY` connection-scaling or event-rate limits being hit in production.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).
