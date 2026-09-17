---
id: ADR-0049
title: Two independent regional deployments
status: accepted
date: 2026-09-13
deciders: [ ]
category: platform
tags: [ platform, deployment ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ADR-0075 ]
relates_to: [ ADR-0037 ]
design: ../../design/platform-topology.md
legacy_id: D49
---

# ADR-0049 — Two independent regional deployments

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D49`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/platform-topology.md`](../../design/platform-topology.md).

---

## 1. Context

ADR-0048's thin runtime seam flagged a multi-cloud placement risk ("risk X5") around where workers and the DBOS system
database run once the harness operates across GCP and AliCloud. The deployment topology needed fixing: one logical
multi-region system, or independent per-region deployments — and, either way, how `graft_tenant_id` and audit data are
scoped across regions.

## 2. Decision

**Deployment topology for the non-Grafana stack: two independent regional deployments** (GCP, AliCloud), each
shared-multi-tenant internally. **Not one logical system.** `graft_tenant_id` is **globally unique across both regions
and externally sourced** from existing platform team metadata — we adopt the key, we do not mint it, which is what makes
a customer spanning both regions coherent. **Data residency: run data, events, artifacts and audit records never leave
their home region.** Cross-region access is a **read-path proxy** — the local API resolves `home_region` from a
globally-replicated, **metadata-only Tenant Directory**, forwards under the caller's identity, and returns without
persisting outside the home region. Audit chains (ADR-0015)
are wholly in-region and anchor to in-region WORM storage. **Resolves ADR-0048's risk X5** (multi-cloud
worker/system-database placement) by construction: each region has its own workers and its own DBOS system database, and
there is no cross-region workflow recovery.

## 3. Considered options

| Option                                                                                    | Verdict     | Why                                                                                                                                                      |
|-------------------------------------------------------------------------------------------|-------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| One logical multi-region system (shared workers / system database across regions)         | ❌ Rejected | Leaves ADR-0048's risk X5 unresolved — would require building cross-region workflow recovery.                                                            |
| Two independent regional deployments (GCP, AliCloud), each internally shared-multi-tenant | ✅ Chosen   | Resolves risk X5 by construction: each region owns its workers and its own DBOS system database, so there is no cross-region workflow recovery to build. |

## 4. Consequences

- **Positive —** risk X5 resolved by construction; verified live against a scratch Postgres (see Verification).
- **Negative / accepted trade —** not one logical system: cross-region reads go through a read-path proxy rather than a
  native join, and
  `graft_tenant_id` must be sourced externally (adopted, not minted) to stay coherent across two independent
  deployments.
- **Follow-on work —** `grafana_org_id` is region-local (ADR-0060,
  `is_global = false`) and must be treated as a mapped attribute, never a key.
- **Revisit trigger —** none observed.

## 5. Verification

- Separate-system-database-per-region topology — verified 2026-09-13 against a live scratch Postgres 16, `dbos==2.31.1`
  (spike S2, experiment E2). Result: pointing `system_database_url` at a dedicated database while
  `application_database_url` pointed elsewhere worked end to end, with DBOS's control-plane tables (`workflow_status`,
  `operation_outputs`, etc.) confined entirely to the dedicated database — bar a small `transaction_outputs` table that
  always accompanies the application database, for `@DBOS.transaction()`-decorated functions. Full experiment log: [
  `../../design/durable-execution.md`](../../design/durable-execution.md) section 4.5.
