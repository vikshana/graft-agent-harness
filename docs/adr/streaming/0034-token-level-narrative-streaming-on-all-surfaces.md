---
id: ADR-0034
title: Token-level narrative streaming on all surfaces
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
legacy_id: D34
---

# ADR-0034 — Token-level narrative streaming on all surfaces

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D34`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Token-level narrative streaming on all surfaces, including Grafana Live** (deliberately overriding an initially-proposed "coarser granularity for Grafana" caution — chosen for UX responsiveness now that chat is a frequent interaction, not an occasional RCA-only one, per ADR-0036). Step/event-level for everything else (tool calls, hypotheses, evidence, plans) on all surfaces except Slack, which is always batched/throttled regardless. **Raw tool output is never streamed verbatim** — always truncated/summarised inline (Tool Gateway result-reduction, ties to `context-management`), with the untruncated artifact fetched on demand via `GET /runs/{id}/events/{graft_event_id}/artifact` (object storage per ADR-0030), rendered per content type: log viewer, JSON viewer, and specifically a **diff view** for proposed dashboard/alert-rule changes so an approving user can evaluate an `action_proposed` event properly before confirming.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
