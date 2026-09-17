---
id: ADR-0033
title: The back-channel is plain REST
status: accepted
date: 2026-09-12
deciders: [ ]
category: streaming
tags: [ streaming, events ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ADR-0045 ]
relates_to: [ ]
design: ../../design/streaming-and-events.md
legacy_id: D33
---

# ADR-0033 — The back-channel is plain REST

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D33`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

Alongside the one-way event stream (ADR-0006), surfaces need a back-channel for user-initiated actions on a live run —
cancel, signal, approve, request/release control — that works identically across web, Grafana and Slack, before a
durable-execution engine's own signal primitives were chosen. A transport and a provisional signal-delivery mechanism
both needed picking.

## 2. Decision

**Back-channel (cancel/signal/approve/request-control/release-control) is plain REST**, idempotency-keyed to the run,
identical across web, Grafana, and Slack — **locks R7** (superseding its "recommendation" status). Non-driver callers
are rejected per ADR-0032's soft-lock, or redirected to
`request-control`. **Signal delivery is a Postgres signal table +
`LISTEN/NOTIFY`**, reusing ADR-0030's substrate — **superseded by ADR-0045 (2026-09-12)**: DBOS `send`/`recv` replaces
the bespoke signal table now that the orchestrator is chosen. The REST back-channel itself is unchanged, and ADR-0030's
event log is unaffected. **Cancel/signal is checked at every tool-call boundary** (not only at coarse checkpoints) — a
concrete requirement carried into the durable-execution design: the execution loop needs a signal-check hook between
every tool call, bounding cancel latency to the current tool call's duration.

## 3. Considered options

| Option                                                                                                                   | Verdict     | Why                                                                                                                                                                                                         |
|--------------------------------------------------------------------------------------------------------------------------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A surface-specific back-channel per transport (e.g. WebSocket commands for Grafana Live, a separate mechanism for Slack) | ❌ Rejected | Would fragment cancel/signal/approve semantics across surfaces instead of one identical contract; the migrated register entry frames this as locking R7 against exactly that recommendation.                |
| Plain, idempotency-keyed REST back-channel, identical across all surfaces                                                | ✅ Chosen   | One contract for cancel/signal/approve/request-control/release-control regardless of surface; the provisional Postgres signal table (later superseded by ADR-0045) reused the existing event-log substrate. |

## 4. Consequences

- **Positive —** one identical back-channel contract across web, Grafana and Slack, rather than per-surface variants.
- **Negative / accepted trade —** the original Postgres signal table + `LISTEN/NOTIFY` mechanism was provisional and was
  superseded by ADR-0045 once the durable-execution engine was chosen — the REST back-channel itself did not need to
  change, but its internal signal delivery did.
- **Follow-on work —** the execution loop needs a signal-check hook between every tool call, bounding cancel latency to
  the current tool call's duration (carried forward into ADR-0043).
- **Revisit trigger —** none observed beyond the already-completed ADR-0045 supersession of the signal-delivery
  mechanism.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).
