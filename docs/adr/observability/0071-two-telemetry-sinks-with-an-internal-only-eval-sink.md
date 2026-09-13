---
id: ADR-0071
title: Two telemetry sinks with an internal-only eval sink
status: accepted
date: 2026-09-12
deciders: []
category: observability
tags: [observability, audit, compliance]
supersedes: []
superseded_by: []
amends: [ADR-0008]
amended_by: []
relates_to: [ADR-0040]
design: ../../design/audit-and-attribution.md
legacy_id: null
---

# ADR-0071 — Two telemetry sinks with an internal-only eval sink

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D71`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/audit-and-attribution.md`](../../design/audit-and-attribution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Two sinks, two jobs:** operational observability (traces/metrics/logs) and an **internal-only** trajectory/eval sink. **No product feature may read from the eval sink's API.**

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
