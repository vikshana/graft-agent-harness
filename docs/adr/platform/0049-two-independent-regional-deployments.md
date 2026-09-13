---
id: ADR-0049
title: Two independent regional deployments
status: accepted
date: 2026-09-13
deciders: []
category: platform
tags: [platform, deployment]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/platform-topology.md
legacy_id: D49
---

# ADR-0049 — Two independent regional deployments

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D49`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/platform-topology.md`](../../design/platform-topology.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Deployment topology for the non-Grafana stack: two independent regional deployments** (GCP, AliCloud), each shared-multi-tenant internally. **Not one logical system.** `graft_tenant_id` is **globally unique across both regions and externally sourced** from existing platform team metadata — we adopt the key, we do not mint it, which is what makes a customer spanning both regions coherent. **Data residency: run data, events, artifacts and audit records never leave their home region.** Cross-region access is a **read-path proxy** — the local API resolves `home_region` from a globally-replicated, **metadata-only Tenant Directory**, forwards under the caller's identity, and returns without persisting outside the home region. Audit chains (ADR-0015) are wholly in-region and anchor to in-region WORM storage. **Resolves ADR-0048's risk X5** (multi-cloud worker/system-database placement) by construction: each region has its own workers and its own DBOS system database, and there is no cross-region workflow recovery.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
