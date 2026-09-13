---
id: ADR-0058
title: Schedules are a governed Tenant-scoped resource
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
legacy_id: D58
---

# ADR-0058 — Schedules are a governed Tenant-scoped resource

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D58`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Schedules are a governed, tenant-scoped resource — resolves ADR-0047's risk X6.** A **ceiling on Schedule count per Tenant** plus a **minimum interval** (proposed defaults 10 and 1h, pending real cost data), both `platform_admin`-customisable per ADR-0057. **Versioned policy, never overwritten** (ADR-0016): every create/modify/delete is an audit record naming the Principal. **Schedule consumption counts against the Tenant's monthly quota** — a Schedule is not a budget bypass. **All scheduled Runs are `system_initiated` and therefore structurally read-only (ADR-0013/ADR-0047)**, which bounds Schedule risk to *cost*, not *blast radius* — a Schedule can investigate and report, never act. User-facing uses: recurring proactive health/SLO sweeps, **post-incident follow-up verification** (re-check in 24h that a fix held), config/cost-drift reports, and pre-emptive checks ahead of known high-traffic events. **Platform-internal timers** (infra-memory refresh `*/15`, SA drift reconciliation and rotation per ADR-0053) share the timer substrate but are **not user-facing Schedules** and consume no Tenant ceiling.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
