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

Once runs could be shared (ADR-0032, ADR-0054), a rule was needed for who
may approve a proposed write action on a run: only the person who started
it, or anyone currently viewing/driving it? R4's original rationale
("Bob approves when Alice is offline") assumed transferable approval; the
alternative traded that convenience for unambiguous attribution. A
separate concern — platform-wide break-glass access — also needed a
stance on whether the same actor who can reach every Tenant should also
be able to approve writes in every Tenant.

## 2. Decision

**SUPERSEDED 2026-09-13 by ADR-0065/ADR-0066 — approval now follows the
driver.** The separation-of-duties clause (`platform_admin` may never
approve) survives and is *tightened* in ADR-0065; the initiator-only rule
and its expired-approval revisit metric do not. Original text retained
for the record: **Approval authority is initiator-only in v1.**
`may_approve = principal == run.initiator` **AND** re-authenticated in
Grafana (ADR-0014) **AND** check-then-act passes for that specific action
against the initiator's own Grafana permission (ADR-0023, basic-role
granularity per ADR-0026) **AND** `origin == user_initiated` (ADR-0013).
**Accepted consequence, stated plainly:** an offline initiator makes the
approval non-transferable and the Run expires (ADR-0047, ≥72h) —
deliberately trading R4's original "Bob approves when Alice is offline"
rationale for unambiguous attribution in v1. **Revisit metric (same
pattern as ADR-0024): the expired-approval rate** — Runs closed `expired`
holding a pending `hitl_required`. **`platform_admin` break-glass = read,
cancel and suspend in any Tenant, and explicitly NOT approve** —
separation of duties: the actor who can reach every Tenant must not also
authorise writes in every Tenant. Every break-glass access is a
non-sampled audit record naming the admin, the Tenant and the action.
**Two-person rule deferred** to the HITL session — it is mutually
exclusive with initiator-only by definition.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Transferable approval (any authorised viewer of a shared run may approve, per R4's original "Bob approves when Alice is offline") | ❌ Rejected (at the time) | Traded away for unambiguous attribution — approval must be traceable to a single re-authenticated actor, not any currently-present viewer. |
| Initiator-only approval, with the Run expiring if the initiator never returns | ✅ Chosen (superseded) | Kept attribution unambiguous; accepted the cost that an offline initiator makes the approval non-transferable and the Run simply expires (ADR-0047). |
| Let `platform_admin` break-glass access include approval authority | ❌ Rejected | Separation of duties: the actor who can reach every Tenant must not also be able to authorise writes in every Tenant — break-glass is read/cancel/suspend only. |

## 4. Consequences

- **Positive —** attribution of every approval was unambiguous while this
  ADR was in force; the separation-of-duties rule (`platform_admin` never
  approves) proved durable enough to survive supersession unchanged.
- **Negative / accepted trade —** an offline initiator made an approval
  non-transferable, causing the Run to expire — the exact "Bob approves
  when Alice is offline" convenience R4 wanted was deliberately given up.
- **Follow-on work —** superseded 2026-09-13 by ADR-0065 (approval follows
  the driver) and ADR-0066 (the three-clock liveness model that makes
  that safe); the two-person rule remains deferred to the HITL session.
- **Revisit trigger —** already triggered and resolved: this ADR is
  superseded by ADR-0065/ADR-0066.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).
