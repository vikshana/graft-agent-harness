---
id: ADR-0052
title: A normative glossary owns the ubiquitous language
status: accepted
date: 2026-09-13
deciders: [ ]
category: conventions
tags: [ convention, vocabulary ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../GLOSSARY.md
legacy_id: D52
---

# ADR-0052 — A normative glossary owns the ubiquitous language

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D52`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../GLOSSARY.md`](../../GLOSSARY.md).

---

## 1. Context

Three vocabulary collisions surfaced across the design: "tenant" is already Mimir/Loki's `X-Scope-OrgID`; "org" means
both GrafanaOrg and Slack Enterprise Grid org; "workspace" meant both ours and Slack's. Without a single owning source
for these terms, documents and code would keep re-colliding on the same words with different meanings.

## 2. Decision

**A normative glossary (`../GLOSSARY.md`) owns the ubiquitous language.**
Three collisions forced this: "tenant" is already Mimir/Loki's
`X-Scope-OrgID`; "org" means both GrafanaOrg and Slack Enterprise Grid org;
"workspace" meant both ours and Slack's. Rules: **our own scoping key is prefixed `graft_`**, and **foreign terms are
never used bare** (always
`GrafanaOrg`, `SlackWorkspace`, `SlackEnterprise`, `LGTMTenant`). **ADR-0028 is re-framed**: `slack_enterprise_id` was
never a scoping dimension — it is part of *which external identifier we store for the Slack provider*, a column on a
standard identity-federation table
`principal_identity(graft_principal_id, provider, external_id,
slack_enterprise_id, slack_workspace_id)`. **`graft_principal_id` is ours**
and is the key everything hangs from; `slack_enterprise_id`,
`slack_workspace_id` and `slack_channel_id` are attributes and locators that scope nothing. **v1 supports a single
SlackEnterprise and a single SlackWorkspace**, which is precisely why SlackChannel→Tenant binding is load-bearing: one
Slack install serves every Tenant.

## 3. Considered options

| Option                                                                                                                                                           | Verdict     | Why                                                                                                                                                                                  |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Let each document/team use "tenant", "org", "workspace" as they see fit, disambiguated by context                                                                | ❌ Rejected | Three real collisions already existed (Mimir/Loki tenant, GrafanaOrg vs. Slack org, our workspace vs. Slack workspace) — context-only disambiguation had already failed in practice. |
| A single normative glossary that owns these terms, with foreign terms always qualified (`GrafanaOrg`, `SlackWorkspace`, etc.) and our own keys prefixed `graft_` | ✅ Chosen   | Removes the ambiguity at the naming level rather than relying on readers inferring the right meaning from context.                                                                   |

## 4. Consequences

- **Positive —** ADR-0028 is re-framed correctly: `slack_enterprise_id` is an attribute on the identity-federation
  table, not a scoping dimension;
  `graft_principal_id` is the one key everything hangs from.
- **Negative / accepted trade —** v1 supports only a single SlackEnterprise and a single SlackWorkspace, making
  SlackChannel→Tenant binding load-bearing (one Slack install must serve every Tenant).
- **Follow-on work —** every other ADR and design document must use the glossary's vocabulary rather than inventing
  local synonyms.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../GLOSSARY.md`](../../GLOSSARY.md).
