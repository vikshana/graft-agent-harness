---
id: ADR-0008
title: Instrumentation is OpenLIT plus hand-written spans over OTLP
status: accepted
date: 2026-09-12
deciders: []
category: observability
tags: [observability, audit, compliance]
supersedes: []
superseded_by: []
amends: []
amended_by: [ADR-0071]
relates_to: []
design: ../../design/audit-and-attribution.md
legacy_id: D8
---

# ADR-0008 — Instrumentation is OpenLIT plus hand-written spans over OTLP

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D8`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/audit-and-attribution.md`](../../design/audit-and-attribution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

Instrumentation: **OpenLIT + hand-written spans** for graph nodes and domain semantics → **OTLP → Collector → multi-sink**.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
