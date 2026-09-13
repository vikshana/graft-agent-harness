---
id: ADR-0065
title: Approval authority follows the driver
status: accepted
date: 2026-09-13
deciders: []
category: identity
tags: [identity, authn, authz]
supersedes: [ADR-0055]
superseded_by: []
amends: []
amended_by: []
relates_to: [ADR-0064, ADR-0014]
design: ../../design/external-identity-mapping.md
legacy_id: D65
---

# ADR-0065 — Approval authority follows the driver

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D65`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Approval authority follows the driver, not the initiator — superseding ADR-0055's initiator-only rule.** `may_approve(P, run, action)` = `P == run.control.driver` **AND** re-authenticated in Grafana (ADR-0014) **AND** check-then-act passes for that specific action against **P's own** Grafana permission (ADR-0023, basic-role granularity per ADR-0026) **AND** `run.origin == user_initiated` (ADR-0013) **AND** P's Role holds `action:approve` (ADR-0056). **This closes the on-call handover gap ADR-0055 deliberately accepted**, and trades it for a new, smaller one: **control is now authority**, so every transfer of control is a transfer of approval authority and must be audited as such (ADR-0066). **Three properties make the trade safe.** (1) **A private Run degenerates to the old rule by construction** — it has exactly one participant, who is the driver, so driver-based approval *is* initiator-only there, with no special case. (2) **`viewer` can never drive (no `run:steer` verb, ADR-0056) and therefore can never approve** — the Role lattice already excludes the dangerous case. (3) **Approval binds to `proposal_hash`, never to intent** (audit design), so a driver who inherits a pending proposal approves exactly the artefact that was reviewed; a proposal is **not** invalidated by a control change, because regenerating it would mean re-running the agent and would make handover useless. The approving UI states **“proposed while X was driving; you are approving as Y”** — attribution is explicit, never implied — and the audit chain records proposer-context and approver separately with the control-transfer record as a `caused_by` edge, so the chain shows *how* Y came to hold authority. **ADR-0055's separation of duties is preserved and tightened:** `platform_admin` break-glass is read, cancel and suspend in any Tenant, and explicitly **not** approve, **not** drive, and **not** force-release — force-release is an approval-authority act, so the actor who can reach every Tenant must not hold it. **ADR-0064's “driving is not approving” rationale is deleted**, and the two escape hatches it justified are re-justified on new grounds in ADR-0066. **Two-person rule remains deferred** to the HITL session, and is no longer mutually exclusive with this model — it composes with it. **Revisit metric changes** from ADR-0055's expired-approval rate (now expected to fall sharply) to the **force-release-then-self-approve rate** — see ADR-0066.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
