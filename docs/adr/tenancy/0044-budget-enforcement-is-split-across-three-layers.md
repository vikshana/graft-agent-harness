---
id: ADR-0044
title: Budget enforcement is split across three layers
status: accepted
date: 2026-09-12
deciders: []
category: tenancy
tags: [tenancy, scoping, rbac]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/tenancy-and-scoping.md
legacy_id: D44
---

# ADR-0044 — Budget enforcement is split across three layers

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D44`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Budget/circuit-breaker enforcement is deliberately split across three layers, not accidentally duplicated.** Orchestrator: concurrent runs per workspace via **durable-queue partition keys** (partitioned queues apply concurrency and rate limits **per partition** — a native implementation of **ADR-0017**'s ceiling chain), plus per-run wall-clock via deadlines. Agent: max graph depth (~15), loop breakers (same tool + same args twice), per-run token/cost caps reported via ADR-0029's `budget_consumed`/`budget_warning`. Tool Gateway: per-connection throttles protecting *customer* infrastructure, keyed by connection and independent of workspace quota.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
