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
relates_to: [ADR-0037, ADR-0041, ADR-0060]
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

**Scope of the RLS mechanism, clarified by spike S2 (2026-09-13):** the third mechanism — Postgres RLS on `graft_tenant_id` — applies to tables **we** own and create. It does not, and empirically cannot, extend to DBOS Transact's own control-plane tables (`workflow_status`, `operation_outputs`, `notifications`, etc., ADR-0037). Retrofitting `FORCE ROW LEVEL SECURITY` plus a `graft_tenant_id` policy onto `workflow_status` causes DBOS's own `INSERT` to be **rejected outright by Postgres**, because DBOS never sets `graft.tenant_id` and has no concept of the column — a workflow cannot even start. A permissive `graft_tenant_id IS NULL OR …` policy avoids the error but grants every Tenant unrestricted read/write access to every DBOS row, providing none of this ADR's isolation guarantee — a trap, not a mitigation. **Tenant isolation for DBOS workflow metadata is therefore enforced at the application layer, not by RLS**: DBOS is treated as an internal, tenant-blind control plane, reached only through code that has already authorised the caller's `graft_tenant_id` before ever calling the DBOS SDK, with `dbos_workflow_id = graft_run_id` (ADR-0060) as the join key back to our own RLS-protected `run` table for any tenant-scoped query. Our own tables are unaffected by this limitation and keep the full three-mechanism guarantee, confirmed to survive a transaction-mode pooler (see Verification).

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

**Application-level filtering only (rejected), the Grafana OSS precedent.** Grafana OSS itself does not use `FORCE ROW LEVEL SECURITY` or any database-native isolation mechanism for its own multi-org model: nearly every org-scoped table carries an `org_id` column, the Go backend appends an explicit `WHERE org_id = ?` to queries via its XORM-based store layer, and the application connects to Postgres/MySQL/SQLite through a single shared database role with unrestricted read/write access to every table — there is no per-tenant database principal and no database-enforced boundary at all. This is a real, shipping precedent for "isolation via consistent application code," and it is explicitly rejected here as the sole mechanism: a single missed `WHERE` clause in one code path is a full cross-tenant data leak with no independent backstop, and Grafana's own CVE history includes exactly this class of bug. RLS plus `SET LOCAL` was chosen instead because it makes the database the second, independent enforcement point — a bug in application code fails closed (an empty result set or a rejected write), not open. Spike S2 (2026-09-13) shows this guarantee has a real limit, though: it holds only for tables we own. DBOS Transact's own control-plane tables cannot carry a working RLS policy (see the Decision section below) and fall back to exactly the application-layer-only model Grafana uses — the same trust boundary Grafana accepts for its entire schema, but scoped here to one internal, tenant-blind subsystem rather than every table in the system.

## 4. Consequences

- **Positive —** the three-mechanism boundary holds for every table we own; confirmed empirically (spike S2) to survive pgbouncer transaction-mode pooling under concurrent, alternating-tenant load with zero cross-tenant leakage.
- **Negative / accepted trade —** DBOS's own system tables sit outside this mechanism's reach. A bug that calls the DBOS SDK (e.g. `list_workflows`, `get_workflow_status`) without first checking the caller's `graft_tenant_id` against the run's recorded owner is not caught by a database policy — it must be caught by code review and the isolation test suite (already a Phase 1 exit criterion), not backstopped by Postgres for that specific table set.
- **Follow-on work —** ADR-0048's `runtime` seam is the single chokepoint that must perform this check on every DBOS-facing call; it is where this ADR's guarantee is actually enforced for workflow metadata, not in the database.
- **Revisit trigger —** if a future DBOS release adds a first-class tenant/namespace column to its own schema, this decision should be revisited to add real RLS there instead of relying solely on the application layer.

## 5. Verification

- `FORCE ROW LEVEL SECURITY` + `SET LOCAL graft.tenant_id` on our own tables under pgbouncer transaction-mode pooling — verified 2026-09-13 against a live scratch Postgres 16 + pgbouncer (transaction mode), `dbos==2.31.1` (spike S2, experiment E4). Result: 400 interleaved, alternating-tenant transactions across 4 threads produced **zero** cross-tenant row visibility.
- Retrofitting `FORCE ROW LEVEL SECURITY` + a `graft_tenant_id` policy onto DBOS's own `workflow_status` table — verified 2026-09-13 against the same environment (spike S2, experiment E3). Result: DBOS's own `INSERT` is rejected outright (`new row violates row-level security policy for table "workflow_status"`); a permissive NULL-passthrough policy avoids the error but grants unrestricted cross-tenant read/write access to every DBOS row.
