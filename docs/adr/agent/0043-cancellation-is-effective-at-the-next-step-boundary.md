---
id: ADR-0043
title: Cancellation is effective at the next step boundary
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
legacy_id: D43
---

# ADR-0043 — Cancellation is effective at the next step boundary

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D43`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Cancellation contract: effective at the next step boundary**, so latency is bounded by the current step's duration (a cancel during a 40s PromQL query lands when that query returns) — accepted 2026-09-12; `preemptible=True` steps are **not** used in v1 but remain available if a latency complaint materialises. **Propagation is native**: `timeout_ms`/`deadline_epoch_ms` cancel the workflow **and all its children**, so sub-agent teardown is not hand-rolled. v1 teardown scope = child workflows + pending queue entries; in-flight tool calls complete and are discarded; Phase-2 sandboxes (ADR-0004) are out of scope.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
