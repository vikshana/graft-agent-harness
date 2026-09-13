---
id: ADR-0035
title: Unattended-run notification via Slack summary and in-app inbox
status: accepted
date: 2026-09-12
deciders: []
category: streaming
tags: [streaming, events]
supersedes: []
superseded_by: []
amends: []
amended_by: [ADR-0047]
relates_to: []
design: ../../design/streaming-and-events.md
legacy_id: D35
---

# ADR-0035 — Unattended-run notification via Slack summary and in-app inbox

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D35`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Unattended-run notification: Slack bot posts a completion summary message; Grafana and the web frontend surface an in-app badge/inbox.** No escalation path for unanswered `hitl_required` approvals in v1 (unlike ADR-0024, no revisit-trigger metric defined yet for this one) — the run simply waits for its owner (or, if shared, an authorised viewer) to return; revisit only if real usage shows abandoned approvals becoming a problem.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
