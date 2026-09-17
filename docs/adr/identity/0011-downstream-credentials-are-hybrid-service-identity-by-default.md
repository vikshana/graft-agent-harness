---
id: ADR-0011
title: Downstream credentials are hybrid, service-identity by default
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
legacy_id: D11
---

# ADR-0011 — Downstream credentials are hybrid, service-identity by default

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D11`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

Every tool call needs a downstream credential to present to the target system (Grafana, GitHub, etc.), but
`system_initiated` runs (ADR-0013) and all Slack-initiated runs have no live end-user session to draw one from, while
`user_initiated` runs from the Grafana plugin do. A single strategy was needed that works for both, without silently
discarding the extra precision available when a live user context does exist.

## 2. Decision

Downstream credential strategy is **hybrid, service-identity-by-default**: a workspace service account is always the
fallback (required for `system_initiated` runs, ADR-0013, and for **all Slack-initiated runs**, ADR-0025); user identity
is layered on top via **check-then-act** where a live Grafana request context exists. GitHub always acts as a **bot
identity** (GitHub App), never impersonating the user. **The Grafana workspace service account authenticates via
`Authorization: Bearer glsa_...`, confirmed against Grafana's own docs** — see ADR-0018's expanded note for how this
credential moves through the Tool Gateway → `grafana-mcp` → Grafana hop chain.

## 3. Considered options

| Option                                                                                                                                    | Verdict     | Why                                                                                                                                                                                    |
|-------------------------------------------------------------------------------------------------------------------------------------------|-------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Hybrid: workspace service account by default, user identity layered on top via check-then-act where a live Grafana request context exists | ✅ Chosen   | Always has a fallback identity for surfaces with no session, while still narrowing to the user's own permissions when one is available                                                 |
| Pure user impersonation for every downstream call                                                                                         | ❌ Rejected | Fails outright for `system_initiated` (ADR-0013) and Slack-initiated runs, which have no live user session to impersonate                                                              |
| Service-account-only for every call, including `user_initiated` web/plugin runs                                                           | ❌ Rejected | Throws away the ability to narrow access to the live user's own Grafana permissions (check-then-act), making every action as privileged as the service account regardless of who asked |

## 4. Consequences

- **Positive —** one consistent fallback identity across every surface, with tighter, per-user narrowing available
  wherever a session exists; GitHub's bot-identity rule removes any ambiguity about impersonating a human there.
- **Negative / accepted trade —** two code paths exist (service-account-only vs. service-account-plus-check-then-act),
  which the Tool Gateway must keep straight per call.
- **Follow-on work —** the exact hop chain (Tool Gateway → `grafana-mcp` → Grafana) for the service-account bearer
  credential is detailed in ADR-0018.
- **Revisit trigger —** none observed.

## 5. Verification

- Confirmed against Grafana's own documentation, 2026-09-12: the workspace service account authenticates via
  `Authorization: Bearer glsa_...`. Mechanism:
  [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

