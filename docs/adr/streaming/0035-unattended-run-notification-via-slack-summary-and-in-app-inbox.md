---
id: ADR-0035
title: Unattended-run notification via Slack summary and in-app inbox
status: accepted
date: 2026-09-12
deciders: [ ]
category: streaming
tags: [ streaming, events ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ADR-0047 ]
relates_to: [ ]
design: ../../design/streaming-and-events.md
legacy_id: D35
---

# ADR-0035 — Unattended-run notification via Slack summary and in-app inbox

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D35`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

Runs can complete, or hit a `hitl_required` approval gate, while nobody is watching the live stream. A notification
mechanism was needed so the owner (or, if shared, an authorised viewer) finds out — along with a decision on whether
unanswered approvals should escalate to anyone beyond the original audience.

## 2. Decision

**Unattended-run notification: Slack bot posts a completion summary message; Grafana and the web frontend surface an
in-app badge/inbox.** No escalation path for unanswered `hitl_required` approvals in v1 (unlike ADR-0024, no
revisit-trigger metric defined yet for this one) — the run simply waits for its owner (or, if shared, an authorised
viewer) to return; revisit only if real usage shows abandoned approvals becoming a problem.

## 3. Considered options

| Option                                                                                                  | Verdict              | Why                                                                                                                                                   |
|---------------------------------------------------------------------------------------------------------|----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| Escalate unanswered `hitl_required` approvals to a broader audience after a timeout                     | ❌ Rejected (for v1) | No escalation path defined; the run simply waits, deliberately, until real usage shows abandoned approvals are a problem worth solving.               |
| Slack completion-summary message plus in-app badge/inbox on Grafana and the web frontend, no escalation | ✅ Chosen            | Covers the common notification need (owner finds out when unattended) without building escalation infrastructure before there's evidence it's needed. |

## 4. Consequences

- **Positive —** owners are notified of completion without needing to watch the live stream; no escalation
  infrastructure to build or maintain before it's proven necessary.
- **Negative / accepted trade —** an unanswered `hitl_required` approval has no escalation path in v1 — later bounded by
  ADR-0047, which adds an expiry so the run does not wait indefinitely, though still without escalating to anyone else.
- **Follow-on work —** amended by ADR-0047, which gives HITL approval waits a bounded expiry (closing the run as
  `expired`) rather than leaving them open-ended.
- **Revisit trigger —** real usage showing abandoned approvals becoming a problem.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).
