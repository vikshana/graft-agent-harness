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

ADR-0047's durable-timer decision named recurring/scheduled RCA as a v1
use case, flagging risk X6: an unbounded ability to create schedules could
let a Tenant accumulate unlimited recurring cost, or use a very short
interval to hammer the system. A governance model was needed — ceilings,
audit, and whether scheduled runs count against the same quota as
on-demand runs — before schedules could ship as a user-facing capability.

## 2. Decision

**Schedules are a governed, tenant-scoped resource — resolves ADR-0047's
risk X6.** A **ceiling on Schedule count per Tenant** plus a **minimum
interval** (proposed defaults 10 and 1h, pending real cost data), both
`platform_admin`-customisable per ADR-0057. **Versioned policy, never
overwritten** (ADR-0016): every create/modify/delete is an audit record
naming the Principal. **Schedule consumption counts against the Tenant's
monthly quota** — a Schedule is not a budget bypass. **All scheduled Runs
are `system_initiated` and therefore structurally read-only
(ADR-0013/ADR-0047)**, which bounds Schedule risk to *cost*, not *blast
radius* — a Schedule can investigate and report, never act. User-facing
uses: recurring proactive health/SLO sweeps, **post-incident follow-up
verification** (re-check in 24h that a fix held), config/cost-drift
reports, and pre-emptive checks ahead of known high-traffic events.
**Platform-internal timers** (infra-memory refresh `*/15`, SA drift
reconciliation and rotation per ADR-0053) share the timer substrate but
are **not user-facing Schedules** and consume no Tenant ceiling.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Unbounded Schedule creation, no per-Tenant ceiling or minimum interval | ❌ Rejected | Leaves ADR-0047's risk X6 open — a Tenant could accumulate unlimited recurring cost or hammer the system with a very short interval. |
| Let Schedules bypass the Tenant's monthly budget quota | ❌ Rejected | A Schedule is not a budget bypass — recurring cost must count against the same quota as on-demand runs, or it becomes an unmetered cost path. |
| A per-Tenant Schedule-count ceiling and minimum interval, both platform-customisable, with Schedule consumption counting against the monthly quota | ✅ Chosen | Resolves risk X6 directly; scheduled runs being `system_initiated` and structurally read-only additionally bounds risk to cost, not blast radius. |

## 4. Consequences

- **Positive —** Schedule risk is bounded to cost, not blast radius,
  because every scheduled run is structurally read-only; every
  create/modify/delete is an audited, versioned policy change.
- **Negative / accepted trade —** the proposed defaults (10 schedules per
  Tenant, 1h minimum interval) are provisional, pending real cost data,
  and may need revisiting once usage patterns are known.
- **Follow-on work —** platform-internal timers (infra-memory refresh,
  SA drift reconciliation/rotation) share the same timer substrate but
  must not be mistaken for or counted against user-facing Schedule
  ceilings.
- **Revisit trigger —** real cost data on schedule usage patterns.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).
