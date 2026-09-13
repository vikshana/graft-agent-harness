---
id: ADR-0053
title: Tenant lifecycle is discovered, provisioning, ready, suspended
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
legacy_id: D53
---

# ADR-0053 — Tenant lifecycle is discovered, provisioning, ready, suspended

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D53`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Tenant lifecycle `discovered → provisioning → ready → suspended`, reconciling ADR-0022's synchronous provisioning with hundreds of pre-existing GrafanaOrgs.** A reconciler creates a **credential-less `discovered` row for every existing GrafanaOrg** — free, no service accounts, no cost — so the capability is one admin action away for every team. **`discovered → ready` is the explicit admin act that fires ADR-0022's synchronous SA provisioning**, so ADR-0022 is untouched *and* we never hold hundreds of unused credentials. **One idempotent code path** serves both backfill and new-org creation; no special-case migration script. `suspended` revokes tokens and rejects new Runs without deleting history. **Platform-owned SAs: naming is a signal, reconciliation is the control** — Grafana OSS cannot prevent a GrafanaOrgAdmin editing or deleting them. Reserved prefix `graft-platform-` (`graft-platform-enforcement`, `graft-platform-mcp`) with a “Managed by the Graft platform — do not modify” display name; a **drift reconciler** (scheduled DBOS workflow, ADR-0047) asserts SA existence, minimum role (ADR-0022) and token validity, re-provisioning and auditing on divergence; **rotation is a scheduled workflow, not a calendar reminder**; per-SA metrics: token age, time-to-expiry, last successful use, drift events, re-provisions, reconciler lag.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
