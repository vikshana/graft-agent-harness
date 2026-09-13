---
id: ADR-0015
title: Audit records form an insert-only hash-chained DAG
status: accepted
date: 2026-09-12
deciders: []
category: observability
tags: [observability, audit, compliance]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/audit-and-attribution.md
legacy_id: D15
---

# ADR-0015 — Audit records form an insert-only hash-chained DAG

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D15`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/audit-and-attribution.md`](../../design/audit-and-attribution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Audit records form an insert-only, hash-chained DAG** (`caused_by` edges from trigger → effect), anchored periodically to WORM object storage. Every record derives its `actor` from the verified credential, never from agent/tool output. `graft_run_id` is propagated **outward** into customer-owned logs (K8s `impersonatedBy`, GitHub commit trailers, datasource query headers). **Retention: 12 months minimum, 3 months hot**, set by the confirmed compliance regime (ADR-0025, PCI-DSS).

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
