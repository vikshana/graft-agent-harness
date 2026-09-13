---
id: ADR-0050
title: Isolation is never thread-level
status: accepted
date: 2026-09-13
deciders: []
category: tenancy
tags: [tenancy, scoping, rbac]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/tenancy-and-scoping.md
legacy_id: D50
---

# ADR-0050 — Isolation is never thread-level

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D50`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Isolation is never thread-level.** Parallel execution for hundreds of Principals is a **scheduling** problem, not an isolation one — Python threads share a heap and the primary threat (indirect prompt injection, ADR-0007) does not respect task boundaries. Isolation is exactly three mechanisms, all already locked: the run-scoped capability token (ADR-0010, a Run cannot *name* another Tenant's credentials), Tool Gateway credential resolution by Tenant (ADR-0007/ADR-0070/ADR-0018, never ambient), and Postgres RLS on `graft_tenant_id`. Two hard implementation rules follow: **(1) no ambient or thread-local Tenant context, ever** — scope travels as an explicit argument through ADR-0048's `runtime` seam, since thread-locals plus async task switching is the classic cross-tenant leak; **(2) RLS is established per transaction with `SET LOCAL`, never `SET`** — a transaction-mode pooler reassigns connections between Tenants, and ADR-0048 already named the pooler as the binding scale constraint. Concurrency itself is ADR-0044's partitioned queues keyed by `graft_tenant_id`. `FORCE ROW LEVEL SECURITY` is required, since the application role is typically the table owner and would otherwise bypass every policy.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
