---
id: ADR-0065
title: Approval authority follows the driver
status: accepted
date: 2026-09-13
deciders: [ ]
category: identity
tags: [ identity, authn, authz ]
supersedes: [ ADR-0055 ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ADR-0064, ADR-0014 ]
design: ../../design/external-identity-mapping.md
legacy_id: D65
---

# ADR-0065 — Approval authority follows the driver

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D65`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

ADR-0055 fixed approval authority to the run's initiator only, so that an offline initiator meant the Run simply
expired — an accepted trade at the time. Once ADR-0064 introduced explicit driver handover for shared runs, that trade
reopened as a concrete gap: an on-call handover mid-run left no one able to approve a pending action, because the person
now driving was not the original initiator. A rule was needed for who may approve once control itself can move between
participants.

## 2. Decision

**Approval authority follows the driver, not the initiator — superseding ADR-0055's initiator-only rule.**
`may_approve(P, run, action)` = `P == run.control.driver` **AND** re-authenticated in Grafana (ADR-0014) **AND**
check-then-act passes for that specific action against **P's own** Grafana permission (ADR-0023, basic-role granularity
per ADR-0026) **AND** `run.origin == user_initiated` (ADR-0013) **AND** P's Role holds `action:approve` (ADR-0056).
**This closes the on-call handover gap ADR-0055 deliberately accepted**, and trades it for a new, smaller one: **control
is now authority**, so every transfer of control is a transfer of approval authority and must be audited as such
(ADR-0066). **Three properties make the trade safe.** (1) **A private Run degenerates to the old rule by
construction** — it has exactly one participant, who is the driver, so driver-based approval *is* initiator-only there,
with no special case. (2) **`viewer` can never drive (no `run:steer` verb, ADR-0056) and therefore can never approve** —
the Role lattice already excludes the dangerous case. (3) **Approval binds to `proposal_hash`, never to intent** (audit
design), so a driver who inherits a pending proposal approves exactly the artefact that was reviewed; a proposal is
**not** invalidated by a control change, because regenerating it would mean re-running the agent and would make handover
useless. The approving UI states **“proposed while X was driving; you are approving as Y”** — attribution is explicit,
never implied — and the audit chain records proposer-context and approver separately with the control-transfer record as
a `caused_by` edge, so the chain shows *how* Y came to hold authority. **ADR-0055's separation of duties is preserved
and tightened:** `platform_admin` break-glass is read, cancel and suspend in any Tenant, and explicitly **not** approve,
**not** drive, and **not** force-release — force-release is an approval-authority act, so the actor who can reach every
Tenant must not hold it. **ADR-0064's “driving is not approving” rationale is deleted**, and the two escape hatches it
justified are re-justified on new grounds in ADR-0066. **Two-person rule remains deferred** to the HITL session, and is
no longer mutually exclusive with this model — it composes with it. **Revisit metric changes** from ADR-0055's
expired-approval rate (now expected to fall sharply) to the **force-release-then-self-approve rate** — see ADR-0066.

## 3. Considered options

| Option                                                                                                                                                                                                               | Verdict     | Why                                                                                                                                                                                     |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Approval authority follows the driver (`may_approve` requires `P == run.control.driver`, plus re-authentication, check-then-act on P's own permission, `user_initiated` origin, and a Role holding `action:approve`) | ✅ Chosen   | Closes the on-call handover gap directly: whoever legitimately holds control can also approve, with attribution made explicit in the approving UI                                       |
| Keep ADR-0055's initiator-only rule unchanged                                                                                                                                                                        | ❌ Rejected | Reopens exactly the gap ADR-0064's driver handover was built to close — an offline initiator still blocks approval even when another authorised participant is actively driving         |
| Open approval to any participant with the right Role, not only the current driver                                                                                                                                    | ❌ Rejected | Breaks "control is authority": a non-driving participant could approve an action they are not steering, undermining the audit clarity of "proposed while X was driving; approving as Y" |

## 4. Consequences

- **Positive —** the on-call handover gap is closed; a private Run (exactly one participant) degenerates to the old
  initiator-only behaviour by construction, with no special case; `viewer` can never drive and therefore can never
  approve, so the Role lattice already excludes the dangerous case.
- **Negative / accepted trade —** control is now authority, so every control handover is also an approval-authority
  transfer and must be audited as such (ADR-0066); this raises the stakes of any bug in the three-clock liveness model
  that governs handover and force-release.
- **Follow-on work —** the two-person rule remains deferred to the HITL session but now composes with this model rather
  than being mutually exclusive with it, since it no longer depends on a fixed initiator.
- **Revisit trigger —** the tracked force-release-then-self-approve rate (ADR-0066) shows the new escape hatches are
  being abused.

## 5. Verification

- Not separately verified against a live source; derives from the mechanism verification already done for ADR-0064 and
  ADR-0066. Mechanism:
  [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md); control-liveness mechanism:
  [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

