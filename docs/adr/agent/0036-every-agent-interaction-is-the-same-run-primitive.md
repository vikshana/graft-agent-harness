---
id: ADR-0036
title: Every agent interaction is the same run primitive
status: accepted
date: 2026-09-12
deciders: [ ]
category: agent
tags: [ agent, orchestration, durability ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/durable-execution.md
legacy_id: D36
---

# ADR-0036 — Every agent interaction is the same run primitive

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D36`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

A two-tier split was on the table: lightweight, undurable chat versus heavy, durable RCA investigations — modelled
loosely on the `vikshana-graft-app`
sibling project's stateless, `localStorage`-only chat, and on Grafana Assistant's on-prem/Cloud investigation-tier
split. Whether that split is warranted, or whether every interaction should share one architecture, needed deciding.

## 2. Decision

**Every agent interaction — plain chat, dashboard/alert-building workflows, and RCA investigations — is the same
underlying "run" primitive**, sharing one durable event log (ADR-0030), one audit trail, and one tool-approval mechanism
(ADR-0033). **Runs are user-owned by default** (private, single-user visibility), **explicitly promotable to
workspace-shared** — the act of sharing is what activates ADR-0032's multi-viewer/soft-lock behaviour. **This refines
R4** ("investigations are workspace-owned, not user-owned"): ownership is now a per-run property set at share-time, not
a blanket default for the investigation run-type specifically — reconciled by ADR-0051 and ADR-0054.

## 3. Considered options

| Option                                                                         | Verdict     | Why                                                                                                                                                                                                                      |
|--------------------------------------------------------------------------------|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Two-tier split: lightweight, undurable chat vs. heavy, durable RCA runs        | ❌ Rejected | Even routine chat needs resumable persistence, end-to-end audit, and verified/approved tool calls (e.g. before creating an alert or modifying a dashboard) — requirements that only the full run architecture satisfies. |
| One run primitive for every interaction (chat, dashboard/alert workflows, RCA) | ✅ Chosen   | Shares one durable event log (ADR-0030), one audit trail, and one tool-approval mechanism (ADR-0033) regardless of interaction type.                                                                                     |

## 4. Consequences

- **Positive —** a single architecture (event log, audit, tool-approval)
  serves every interaction type; no separate lightweight-chat code path to maintain or keep consistent with the
  audit/approval guarantees.
- **Negative / accepted trade —** even the lightest chat interaction carries the full run architecture's overhead
  (durable persistence, audit trail), which a dedicated lightweight-chat tier would have avoided.
- **Follow-on work —** refines R4: run ownership is a per-run property set at share-time (private by default, explicitly
  promotable to workspace-shared), not a blanket default tied to the investigation run-type — reconciled by ADR-0051 and
  ADR-0054.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/durable-execution.md`](../../design/durable-execution.md).
