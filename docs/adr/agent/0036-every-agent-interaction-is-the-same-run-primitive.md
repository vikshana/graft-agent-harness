---
id: ADR-0036
title: Every agent interaction is the same run primitive
status: accepted
date: 2026-09-12
deciders: []
category: agent
tags: [agent, orchestration, durability]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/durable-execution.md
legacy_id: D36
---

# ADR-0036 — Every agent interaction is the same run primitive

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D36`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Every agent interaction — plain chat, dashboard/alert-building workflows, and RCA investigations — is the same underlying "run" primitive**, sharing one durable event log (ADR-0030), one audit trail, and one tool-approval mechanism (ADR-0033). An initially-proposed two-tier split ("lightweight, undurable chat" vs. "heavy, durable RCA runs" — modelled loosely on the `vikshana-graft-app` sibling project's stateless, `localStorage`-only chat and on Grafana Assistant's on-prem/Cloud investigation-tier split) was **considered and rejected in this session**, because even routine chat here needs resumable persistence, end-to-end audit, and verified/approved tool calls (e.g. before creating an alert or modifying a dashboard) — requirements that only the full run architecture satisfies. **Runs are user-owned by default** (private, single-user visibility), **explicitly promotable to workspace-shared** — the act of sharing is what activates ADR-0032's multi-viewer/soft-lock behaviour. **This refines R4** ("investigations are workspace-owned, not user-owned"): ownership is now a per-run property set at share-time, not a blanket default for the investigation run-type specifically — reconciled by ADR-0051 and ADR-0054.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
