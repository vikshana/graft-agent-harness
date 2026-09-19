---
id: ADR-0073
title: DBOS system database is separate and PCI-scoped
status: accepted
date: 2026-09-17
deciders: []
category: platform
tags: [dbos, postgres, pci, tenancy]
supersedes: []
superseded_by: []
amends: [ADR-0025, ADR-0041, ADR-0048, ADR-0049, ADR-0050]
amended_by: []
relates_to: [ADR-0037, ADR-0060]
design: ../../design/durable-execution.md
verified: 2026-09-13
---

# ADR-0073 — DBOS system database is separate and PCI-scoped

> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism:
> [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

DBOS persists workflow inputs, outputs, step results and message bodies in its
own serialised tables. Its schema is tenant-blind: DBOS does not set
`graft.tenant_id` and does not provide a `graft_tenant_id` column for its
control-plane rows. Retrofitting `FORCE ROW LEVEL SECURITY` onto those tables
therefore either prevents DBOS from starting workflows or permits every Tenant
to read every DBOS row. The system database also needs to coexist with
transaction-mode poolers, blue/green migrations and the PCI-DSS boundary.

## 2. Decision

Each region uses a dedicated DBOS system database, independently configured
from the application database, while retaining the small DBOS application-side
`transaction_outputs` footprint. DBOS-owned tables are isolated through the
`runtime` seam and the `dbos_workflow_id = graft_run_id` join to our
RLS-protected tables, not through a fabricated tenant RLS policy. The system
database is inside PCI-DSS scope, and the pointer-only step-output rule is a
hard CI-enforced invariant.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Dedicated system database per region, with application-layer authorisation for DBOS metadata | ✅ Chosen | Separates the bulk control-plane state, works with independent DBOS URLs and preserves the explicit runtime seam without a non-functional RLS retrofit. |
| Put all DBOS tables beside application tables and apply `FORCE ROW LEVEL SECURITY` | ❌ Rejected | DBOS does not populate `graft_tenant_id`; a strict policy rejects its writes and a NULL-passthrough policy grants unrestricted cross-Tenant access. |
| Treat DBOS metadata as outside PCI-DSS scope | ❌ Rejected | Inputs, outputs and messages are recoverable from pickle/base64 values; a raw PAN reaches the system tables if the pointer rule is violated. |

## 4. Consequences

- **Positive —** the regional topology is explicit, migration roles can be split from runtime roles, and transaction-mode pooling remains viable.
- **Negative / accepted trade —** DBOS metadata lacks a database-level RLS backstop and the system database inherits PCI-DSS scrubbing, access-control and retention requirements.
- **Follow-on work —** implement the pointer checker in `scripts/check_step_pointer_rule.py` and enforce it when the Phase 1 application package exists; the checker currently operates on future Python source because this repository has no application code yet.
- **Revisit trigger —** a DBOS release that adds a first-class tenant/namespace column and usable RLS semantics to its own schema.

## 5. Verification

Spike S2 was run against Postgres 16, transaction-mode PgBouncer and
`dbos==2.31.1` on 2026-09-13. E2 confirmed independent system and application
database URLs; E3 confirmed that a strict tenant policy rejects DBOS writes and
a NULL-passthrough policy leaks rows; E4 confirmed `SET LOCAL` behaviour through
the pooler; E6 confirmed out-of-band migration; and E7 recovered a test PAN
from `workflow_status.inputs`, `workflow_status.output` and
`operation_outputs.output`. The verified findings are retained in this ADR;
the temporary spike evidence directory is no longer present.


