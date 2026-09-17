---
id: ADR-0020
title: Slack account linking uses Sign in with Slack (OIDC)
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
legacy_id: D20
---

# ADR-0020 — Slack account linking uses Sign in with Slack (OIDC)

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D20`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

Slack account linking (binding a `slack_user_id` to a `graft_principal_id`)
needs an authentication flow, and it needs to be one that actually proves control of the Slack identity rather than
merely asserting it. Hand-rolling an OAuth flow against Slack's APIs was one path; using Slack's own identity layer was
another.

## 2. Decision

**Slack account linking (A3) uses "Sign in with Slack" (OpenID Connect)** rather than a bespoke OAuth flow. Strengthens
the one-time link step only; does not change ADR-0014. **Verified live against `docs.slack.dev`, 2026-09-12** — OIDC
flow, scopes, and endpoints confirmed as described.

## 3. Considered options

| Option                                                                     | Verdict     | Why                                                                                                                                                            |
|----------------------------------------------------------------------------|-------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Sign in with Slack (OpenID Connect)                                        | ✅ Chosen   | Standards-based, verified live against Slack's own docs; reuses a flow Slack already operates rather than one the harness has to maintain                      |
| Bespoke OAuth 2.0 flow hand-rolled against Slack's Web API                 | ❌ Rejected | Reimplements a standard flow Slack already exposes as OIDC, with no advantage and more surface to get wrong (token validation, scope handling)                 |
| No linking flow — trust the `user_id` in the Slack event envelope directly | ❌ Rejected | Never proves control of the identity; fails ADR-0061's mandatory-verified-linking requirement outright, since there is no authenticated round trip to point to |

## 4. Consequences

- **Positive —** a standards-based flow that was later promoted from a one-time convenience to a hard precondition for
  any human-attributed Slack action (ADR-0061).
- **Negative / accepted trade —** none beyond depending on Slack continuing to operate its OIDC endpoint as documented.
- **Follow-on work —** the same signed-deep-link mechanism this flow establishes is reused by ADR-0014's approval
  hand-off from Slack to Grafana.
- **Revisit trigger —** none observed.

## 5. Verification

- Verified live 2026-09-12 against `docs.slack.dev`: OIDC flow, scopes, and endpoints confirmed as described. Mechanism:
  [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

