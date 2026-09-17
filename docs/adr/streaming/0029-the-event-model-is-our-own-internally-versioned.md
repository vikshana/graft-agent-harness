---
id: ADR-0029
title: The event model is our own, internally versioned
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
legacy_id: D29
---

# ADR-0029 — The event model is our own, internally versioned

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D29`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

Given a decoupled event log (ADR-0006), the event schema itself needed choosing: adopt an external protocol like AG-UI,
or own the schema ourselves. AG-UI's React/SSE-shaped client has no natural bridge to Grafana Live's channel/DataFrame
model, which is the primary v1 surface.

## 2. Decision

**Event model is our own, internally owned and versioned**
(`event_version` field on every event, additive-only evolution; adapters must ignore unknown event types gracefully).
**AG-UI is, at most, a future output adapter for the custom web frontend only** — never for Grafana (its
React/SSE-shaped client has no natural bridge to Grafana Live's channel/DataFrame model) and never for Slack. Taxonomy
(v1): `token`,
`agent_thought`, `plan_updated`, `tool_call_start`, `tool_call_result`,
`status`, `evidence_added`, `hypothesis_updated`, `confidence_changed`,
`action_proposed`, `action_confirmed`, `action_executed`,
`sub_agent_spawned`, `hitl_required`, `budget_consumed`,
`budget_warning`, `error`, `done`.

## 3. Considered options

| Option                                                                                                         | Verdict     | Why                                                                                                                                                        |
|----------------------------------------------------------------------------------------------------------------|-------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Adopt AG-UI as the primary event protocol for all surfaces                                                     | ❌ Rejected | Its React/SSE-shaped client has no natural bridge to Grafana Live's channel/DataFrame model — the primary v1 surface — and Slack has no use for it either. |
| Own event model, internally versioned, with AG-UI at most as a future adapter for the custom web frontend only | ✅ Chosen   | Fits all v1 surfaces natively; keeps the option open to add an AG-UI adapter later for the one surface (custom web) where it would actually fit.           |

## 4. Consequences

- **Positive —** the event taxonomy is shaped around what our surfaces actually need (Grafana Live, Slack), not around a
  protocol designed for a different client shape.
- **Negative / accepted trade —** additive-only evolution requires every adapter to tolerate unknown event types
  gracefully, rather than assuming a closed, versioned protocol handles compatibility for us.
- **Follow-on work —** an AG-UI adapter remains a possible future addition, scoped only to the post-v1 custom web
  frontend.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).
