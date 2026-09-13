---
id: ADR-0055
title: Approval authority is initiator-only
status: superseded
date: 2026-09-13
deciders: []
category: tenancy
tags: [tenancy, scoping, rbac]
supersedes: []
superseded_by: [ADR-0065, ADR-0066]
amends: []
amended_by: []
relates_to: []
design: ../../design/tenancy-and-scoping.md
legacy_id: D55
---

# ADR-0055 — Approval authority is initiator-only

> **Status: superseded (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D55`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**SUPERSEDED 2026-09-13 by ADR-0065/ADR-0066 — approval now follows the driver.** The separation-of-duties clause (`platform_admin` may never approve) survives and is *tightened* in ADR-0065; the initiator-only rule and its expired-approval revisit metric do not. Original text retained for the record: **Approval authority is initiator-only in v1.** `may_approve = principal == run.initiator` **AND** re-authenticated in Grafana (ADR-0014) **AND** check-then-act passes for that specific action against the initiator's own Grafana permission (ADR-0023, basic-role granularity per ADR-0026) **AND** `origin == user_initiated` (ADR-0013). **Accepted consequence, stated plainly:** an offline initiator makes the approval non-transferable and the Run expires (ADR-0047, ≥72h) — deliberately trading R4's original “Bob approves when Alice is offline” rationale for unambiguous attribution in v1. **Revisit metric (same pattern as ADR-0024): the expired-approval rate** — Runs closed `expired` holding a pending `hitl_required`. **`platform_admin` break-glass = read, cancel and suspend in any Tenant, and explicitly NOT approve** — separation of duties: the actor who can reach every Tenant must not also authorise writes in every Tenant. Every break-glass access is a non-sampled audit record naming the admin, the Tenant and the action. **Two-person rule deferred** to the HITL session — it is mutually exclusive with initiator-only by definition.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
