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
relates_to: [ADR-0037, ADR-0041]
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

**Confirmed in scope by spike S2 (2026-09-13): the DBOS system database (ADR-0037) is in PCI-DSS scope.** It persists step return values, workflow inputs/outputs and `send`/`recv` message bodies in a recoverable, not encrypted or redacted, wire format. It is **not** exempt as "just orchestration metadata" — anything that reaches those fields, including an accidental PAN quoted from an investigated log line, lands there in plaintext. ADR-0041's pointer rule is the structural mitigation and is now CI-enforced; the system database inherits this ADR's PAN-scrubbing requirement and ADR-0015's retention regime rather than being treated as out of scope.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

- **Positive —** the compliance boundary is unambiguous: PCI-DSS applies platform-wide, including to durable-execution state, not only to customer-facing data paths.
- **Negative / accepted trade —** the DBOS system database (ADR-0037) must be treated as PCI-DSS scope for retention and access-control purposes, not just the audit chain and eval sink originally envisioned — widening the surface the eventual PAN detector and retention tooling must cover.
- **Follow-on work —** the Evals & Benchmarks session's PAN detector must also account for the DBOS system database as a landing zone if the pointer rule (ADR-0041) is ever violated.
- **Revisit trigger —** none observed; scope is now closed rather than provisional (ADR-0037's risk X1 is resolved).

## 5. Verification

- DBOS system-database PCI scope — verified 2026-09-13 against a live scratch Postgres 16, `dbos==2.31.1` (spike S2, experiment E7). Result: a step deliberately returning a raw string containing a test PAN was found, unmodified and trivially recoverable (`base64.b64decode` + `pickle.loads`), in `workflow_status.inputs`, `workflow_status.output` and `operation_outputs.output`. Full experiment log: [`../../design/durable-execution.md`](../../design/durable-execution.md) section 4.5.
