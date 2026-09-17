---
id: ADR-0006
title: Streaming is decoupled from orchestration via a durable event log
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
legacy_id: D6
---

# ADR-0006 — Streaming is decoupled from orchestration via a durable event log

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D6`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

Runs need to stream progress to three very different surfaces — the Grafana plugin, Slack, and (post-v1) a custom web
frontend — each with different transport capabilities. Coupling the streaming mechanism directly to the orchestration
engine's own internals would tie every surface's shape to whatever the durable-execution engine happens to expose, and
would make adding a new surface a change to the orchestrator itself.

## 2. Decision

Streaming is **decoupled from orchestration** via a durable event log. One internal event model; surfaces are thin
adapters.

## 3. Considered options

| Option                                                                                              | Verdict     | Why                                                                                                                                                         |
|-----------------------------------------------------------------------------------------------------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Stream directly from orchestration engine internals to each surface                                 | ❌ Rejected | The migrated register entry did not record a rejection rationale beyond the decision itself; couples every surface's shape to the orchestrator's internals. |
| A durable event log as the single internal event model, with each surface as a thin adapter over it | ✅ Chosen   | Decouples surfaces from the orchestrator; adding a new surface means writing a new thin adapter, not changing orchestration.                                |

## 4. Consequences

- **Positive —** surfaces (Grafana, Slack, future web frontend) are thin adapters over one event model; the
  orchestrator's internals are never exposed directly to any surface.
- **Negative / accepted trade —** every surface-visible event must first be expressed in the internal event model, even
  if a surface's native streaming mechanism could have represented it more directly.
- **Follow-on work —** the event model's content and versioning is decided separately in ADR-0029; the log's storage
  substrate in ADR-0030; per-surface transport in ADR-0031 (Grafana) and elsewhere.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).
