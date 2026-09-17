---
id: ADR-0061
title: Identity linking is mandatory and verified
status: accepted
date: 2026-09-13
deciders: [ ]
category: identity
tags: [ identity, authn, authz ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/external-identity-mapping.md
legacy_id: D61
---

# ADR-0061 — Identity linking is mandatory and verified

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D61`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

A single Slack workspace install (ADR-0052) does not imply a single identity — a human's Slack identity and their Graft
identity are still two different things that must be bound together, and ADR-0015's audit model requires every actor to
derive from a verified credential. Without a hard rule, an unlinked or unverified Slack user could act with no
`graft_principal_id` to attribute the action to, which is incompatible with a compliant audit record and with any
approval model that depends on a resolved Principal.

## 2. Decision

**Identity linking is mandatory and verified: Graft never acts on behalf of a human whose identity is not verifiably
linked for the surface they are acting from.** A single Slack install (ADR-0052) does **not** imply a single identity —
every Tenant and every human must authenticate to Graft so identity maps across systems. An unlinked or unverified
SlackUser gets a **link prompt, not a Run** (ephemeral message, signed single-use “Sign in with Slack” link); a linked
Principal with no Role in the resolved Tenant gets an explicit “ask your `tenant_admin`” refusal, not a generic error.
**`verified_at IS NULL` means *claimed*, and grants nothing** — a mapping becomes verified only via an authenticated
round trip proving control of the external identity (ADR-0020's OIDC flow). **This promotes ADR-0020 from a one-time
convenience to a precondition.** Rationale: **ADR-0015** requires the audit actor to derive from a verified credential,
so an unlinked SlackUser cannot produce a compliant audit record — there is no `graft_principal_id` to attribute to; and
**ADR-0055**'s initiator-only approval is meaningless without a resolved Principal. **ADR-0024 is unchanged and
clarified:** the Tenant service-account ceiling governs *authorisation*, linking governs *attribution* — we must know
who asked even when the permission check does not use their identity, and ADR-0024's own revisit metric is only
computable if we do. `system_initiated` Runs have no human to link and remain bounded by the SA and structurally
read-only (ADR-0013). **`sync_source`** on each mapping (after incident.io's `sync_id`) records which process created
it, and **a reconciler may only delete mappings it owns** — without which ADR-0053's backfill reconciler could remove an
admin's hand-made binding, the classic destructive-sync incident.

## 3. Considered options

| Option                                                                                                                                          | Verdict     | Why                                                                                                                                                                                                        |
|-------------------------------------------------------------------------------------------------------------------------------------------------|-------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Mandatory, verified linking: Graft never acts on behalf of a human whose identity is not verifiably linked for the surface they are acting from | ✅ Chosen   | The only model that guarantees every attributed action has a `graft_principal_id` behind it, satisfying ADR-0015's audit requirement and giving approval authority (ADR-0065) something to resolve against |
| Optional linking, with best-effort attribution when no link exists                                                                              | ❌ Rejected | Cannot produce a compliant audit record per ADR-0015 when no link exists; approval authority has no Principal to resolve to                                                                                |
| Infer the link automatically, e.g. by matching Slack profile email to a known Principal                                                         | ❌ Rejected | Email is never a join key (ADR-0060 section 4.1) — it is mutable and reassignable, so an inferred match risks silently attributing actions to the wrong person                                             |

## 4. Consequences

- **Positive —** an unlinked or unverified user gets a clear link prompt instead of a silently degraded or misattributed
  Run; a linked Principal with no Role gets an explicit "ask your `tenant_admin`" refusal rather than a generic error.
- **Negative / accepted trade —** first-time Slack users face a link-prompt-to-completion step before any action can
  proceed on their behalf, adding friction to the Slack surface's first interaction.
- **Follow-on work —** track the link-prompt-to-completion rate (the design doc's open item); `sync_source` on each
  mapping (ADR-0060) prevents a reconciler from deleting a hand-made binding it doesn't own.
- **Revisit trigger —** the link-prompt friction metric shows the Slack surface is under-delivering because of it.

## 5. Verification

- Not separately verified against a live source beyond the OIDC flow this depends on (ADR-0020's verification).
  Mechanism:
  [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md)
  section 5.

