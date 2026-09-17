---
id: ADR-0013
title: system_initiated runs are structurally read-only
status: accepted
date: 2026-09-12
deciders: [ ]
category: identity
tags: [ identity, authn, authz ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/external-identity-mapping.md
legacy_id: D13
---

# ADR-0013 — system_initiated runs are structurally read-only

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D13`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

`system_initiated` runs (Schedules, webhooks — no human present) can still propose write actions, but nothing is
watching them execute in real time. A decision was needed on how to bound their blast radius: rely on a policy check
that a bug could bypass, or make the class of run structurally incapable of writing at all.

## 2. Decision

**`system_initiated` runs (no human present) are structurally read-only.** Enforced by the run's capability token never
containing a write tool class — not by a policy check that could be bypassed. A human approving a proposal upgrades the
run to `user_initiated` from that point.

## 3. Considered options

| Option                                                                                          | Verdict     | Why                                                                                                                        |
|-------------------------------------------------------------------------------------------------|-------------|----------------------------------------------------------------------------------------------------------------------------|
| Structural enforcement: the run's capability token (ADR-0010) never contains a write tool class | ✅ Chosen   | Cannot be bypassed by a policy-check bug elsewhere — the write path simply does not exist in the token the run is given    |
| Policy-only check at tool-call time (e.g. deny writes if `origin == system_initiated`)          | ❌ Rejected | Relies on every enforcement code path getting the check right, every time; a single missed check anywhere reopens the hole |
| Disallow `system_initiated` runs entirely                                                       | ❌ Rejected | Defeats the purpose of Schedules and webhook-triggered runs, which are the whole point of unattended automation            |

## 4. Consequences

- **Positive —** an unattended run cannot cause a destructive change even under a bug in an unrelated enforcement path,
  because the write class is structurally absent from its token.
- **Negative / accepted trade —** any legitimately useful automated write still requires a human to approve a proposal
  before it executes, adding a step even when the automation "knows" the right action.
- **Follow-on work —** a human approving a proposal upgrades the run to
  `user_initiated` from that point (ADR-0014), which must be reflected consistently in the token and the audit trail.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

