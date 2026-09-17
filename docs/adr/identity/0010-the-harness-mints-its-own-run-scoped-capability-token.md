---
id: ADR-0010
title: The harness mints its own run-scoped capability token
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
legacy_id: D10
---

# ADR-0010 — The harness mints its own run-scoped capability token

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D10`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

Every tool call the agent makes must be independently authorisable by the Tool Gateway without the Gateway trusting the
agent worker's own say-so about who it is acting for, and without depending on a live end-user session —
`system_initiated` runs (ADR-0013) and Slack-triggered runs have none. A credential was needed that is scoped tightly
enough that leaking or reusing it does damage limited to a single run, and that the Gateway can validate on its own.

## 2. Decision

The harness mints its **own short-lived (~10 min), run-scoped, audience-restricted session/capability token**,
independently validated by the Tool Gateway. Revocation via deny-list + short TTL.

## 3. Considered options

| Option                                                                    | Verdict     | Why                                                                                                                                                                                       |
|---------------------------------------------------------------------------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Harness mints its own short-lived, run-scoped, audience-restricted token  | ✅ Chosen   | Scopes blast radius to one run; independently validated by the Tool Gateway; works identically whether or not a human session exists                                                      |
| Forward the driver's/initiator's own IdP session token to every tool call | ❌ Rejected | No live session exists for `system_initiated` or Slack-initiated runs (ADR-0013); would also tie tool-call authorisation to a token whose lifetime and scope the harness does not control |
| Long-lived per-tenant API key shared across runs                          | ❌ Rejected | A single leaked key compromises every run for a Tenant, not one; revocation forces rotating every consumer at once                                                                        |

## 4. Consequences

- **Positive —** clean revocation surface: short TTL (~10 min) plus a deny-list bounds the damage of a leaked token
  almost immediately, and the Tool Gateway validates it without depending on the harness being reachable at call time.
- **Negative / accepted trade —** the harness must operate its own token issuance and signing infrastructure (the MCP
  Authorization Server, ADR-0019) rather than delegating that to an existing IdP.
- **Follow-on work —** deny-list storage and short-TTL renewal logic for long-running runs that outlive one token's
  lifetime.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

