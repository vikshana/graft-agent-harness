---
id: ADR-0025
title: Compliance regime for v1 is PCI-DSS
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
legacy_id: D25
---

# ADR-0025 — Compliance regime for v1 is PCI-DSS

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D25`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/audit-and-attribution.md`](../../design/audit-and-attribution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Compliance regime for v1 is PCI-DSS.** Drives ADR-0015's retention figure and adds a **PAN/cardholder-data scrubbing requirement** to the OTel Collector's existing PII-scrubbing layer (ADR-0008) — must detect and strip primary account numbers before they reach either the audit chain or the eval sink, not merely redact after the fact. Also reinforces (does not change) the step-up-auth (ADR-0016), least-privilege (ADR-0022), and tamper-evidence (ADR-0015) designs already in place, each of which maps to a specific PCI-DSS requirement (8.4.2, least-privilege reviews, 10.5.2 respectively). **PAN-scrubbing implementation (the Luhn-check-backed detector) is deferred to the Evals & Benchmarks deep-dive session (2026-09-12 decision)** — the requirement itself is locked, only the implementation session is deferred.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
