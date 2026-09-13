---
id: ADR-0041
title: Step granularity is one LLM call or one tool call
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
legacy_id: D41
---

# ADR-0041 — Step granularity is one LLM call or one tool call

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D41`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Step granularity (the briefing's "crux"): one LLM call = one step; one tool call = one step; one sub-agent = one child workflow; one run = one parent workflow.** Consequences: retry waste is bounded to a single LLM call (accepted); **ADR-0033's "signal check at every tool-call boundary" is satisfied structurally** rather than by a bespoke hook, since cancel preempts at step boundaries and every tool call is a step; write amplification is one ~1–2 ms Postgres write per step (accepted, against DBOS's >40K steps/sec single-Postgres benchmark). **Steps must return pointers, never large payloads** — artifacts go to object storage, which ADR-0034 already requires independently.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
