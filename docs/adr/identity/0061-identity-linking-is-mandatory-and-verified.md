---
id: ADR-0061
title: Identity linking is mandatory and verified
status: accepted
date: 2026-09-13
deciders: []
category: identity
tags: [identity, authn, authz]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/external-identity-mapping.md
legacy_id: D61
---

# ADR-0061 — Identity linking is mandatory and verified

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D61`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Identity linking is mandatory and verified: Graft never acts on behalf of a human whose identity is not verifiably linked for the surface they are acting from.** A single Slack install (ADR-0052) does **not** imply a single identity — every Tenant and every human must authenticate to Graft so identity maps across systems. An unlinked or unverified SlackUser gets a **link prompt, not a Run** (ephemeral message, signed single-use “Sign in with Slack” link); a linked Principal with no Role in the resolved Tenant gets an explicit “ask your `tenant_admin`” refusal, not a generic error. **`verified_at IS NULL` means *claimed*, and grants nothing** — a mapping becomes verified only via an authenticated round trip proving control of the external identity (ADR-0020's OIDC flow). **This promotes ADR-0020 from a one-time convenience to a precondition.** Rationale: **ADR-0015** requires the audit actor to derive from a verified credential, so an unlinked SlackUser cannot produce a compliant audit record — there is no `graft_principal_id` to attribute to; and **ADR-0055**'s initiator-only approval is meaningless without a resolved Principal. **ADR-0024 is unchanged and clarified:** the Tenant service-account ceiling governs *authorization*, linking governs *attribution* — we must know who asked even when the permission check does not use their identity, and ADR-0024's own revisit metric is only computable if we do. `system_initiated` Runs have no human to link and remain bounded by the SA and structurally read-only (ADR-0013). **`sync_source`** on each mapping (after incident.io's `sync_id`) records which process created it, and **a reconciler may only delete mappings it owns** — without which ADR-0053's backfill reconciler could remove an admin's hand-made binding, the classic destructive-sync incident.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
