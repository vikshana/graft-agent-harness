---
id: ADR-0015
title: Audit records form an insert-only hash-chained DAG
status: accepted
date: 2026-09-12
deciders: [ ]
category: observability
tags: [ observability, audit, compliance ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/audit-and-attribution.md
legacy_id: D15
---

# ADR-0015 — Audit records form an insert-only hash-chained DAG

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D15`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/audit-and-attribution.md`](../../design/audit-and-attribution.md).

---

## 1. Context

Audit records need to be tamper-evident and correctly attributed to the acting identity, across a chain of
causally-related events (e.g. a trigger followed by an effect it caused), and a retention policy needed setting that
satisfies whatever compliance regime v1 targets (ADR-0025).

## 2. Decision

**Audit records form an insert-only, hash-chained DAG** (`caused_by` edges from trigger → effect), anchored periodically
to WORM object storage. Every record derives its `actor` from the verified credential, never from agent/tool output.
`graft_run_id` is propagated **outward** into customer-owned logs (K8s `impersonatedBy`, GitHub commit trailers,
datasource query headers). **Retention: 12 months minimum, 3 months hot**, set by the confirmed compliance regime
(ADR-0025, PCI-DSS).

## 3. Considered options

| Option                                                                                            | Verdict     | Why                                                                                                                                                             |
|---------------------------------------------------------------------------------------------------|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Derive `actor` from agent/tool output (e.g. a claimed identity in a tool call payload)            | ❌ Rejected | Agent/tool output is not a verified credential; an audit record's actor must be trustworthy by construction, not by what the model happened to say.             |
| Insert-only, hash-chained DAG of audit records, `actor` derived only from the verified credential | ✅ Chosen   | Tamper-evident (hash chain, WORM anchoring) and correctly attributed (verified credential, never agent output); `caused_by` edges make causal chains queryable. |

## 4. Consequences

- **Positive —** the audit trail is tamper-evident (hash chain anchored to WORM storage) and attribution cannot be
  spoofed by agent or tool output.
- **Negative / accepted trade —** retention is fixed at 12 months minimum (3 hot), driven by PCI-DSS (ADR-0025) rather
  than being a tunable product choice.
- **Follow-on work —** `graft_run_id` must be propagated outward into customer-owned logs (K8s `impersonatedBy`, GitHub
  commit trailers, datasource query headers) so audit trails are traceable at the customer's own log boundary too.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/audit-and-attribution.md`](../../design/audit-and-attribution.md).
