---
id: ADR-0029
title: The event model is our own, internally versioned
status: accepted
date: 2026-09-12
deciders: []
category: streaming
tags: [streaming, events]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/streaming-and-events.md
legacy_id: D29
---

# ADR-0029 — The event model is our own, internally versioned

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D29`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Event model is our own, internally owned and versioned** (`event_version` field on every event, additive-only evolution; adapters must ignore unknown event types gracefully). **AG-UI is, at most, a future output adapter for the custom web frontend only** — never for Grafana (its React/SSE-shaped client has no natural bridge to Grafana Live's channel/DataFrame model) and never for Slack. Taxonomy (v1): `token`, `agent_thought`, `plan_updated`, `tool_call_start`, `tool_call_result`, `status`, `evidence_added`, `hypothesis_updated`, `confidence_changed`, `action_proposed`, `action_confirmed`, `action_executed`, `sub_agent_spawned`, `hitl_required`, `budget_consumed`, `budget_warning`, `error`, `done`.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
