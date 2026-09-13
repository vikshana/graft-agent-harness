---
id: ADR-0052
title: A normative glossary owns the ubiquitous language
status: accepted
date: 2026-09-13
deciders: []
category: conventions
tags: [convention, vocabulary]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../GLOSSARY.md
legacy_id: D52
---

# ADR-0052 — A normative glossary owns the ubiquitous language

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D52`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../GLOSSARY.md`](../../GLOSSARY.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**A normative glossary (`../GLOSSARY.md`) owns the ubiquitous language.** Three collisions forced this: “tenant” is already Mimir/Loki's `X-Scope-OrgID`; “org” means both GrafanaOrg and Slack Enterprise Grid org; “workspace” meant both ours and Slack's. Rules: **our own scoping key is prefixed `graft_`**, and **foreign terms are never used bare** (always `GrafanaOrg`, `SlackWorkspace`, `SlackEnterprise`, `LGTMTenant`). **ADR-0028 is re-framed**: `slack_enterprise_id` was never a scoping dimension — it is part of *which external identifier we store for the Slack provider*, a column on a standard identity-federation table `principal_identity(graft_principal_id, provider, external_id, slack_enterprise_id, slack_workspace_id)`. **`graft_principal_id` is ours** and is the key everything hangs from; `slack_enterprise_id`, `slack_workspace_id` and `slack_channel_id` are attributes and locators that scope nothing. **v1 supports a single SlackEnterprise and a single SlackWorkspace**, which is precisely why SlackChannel→Tenant binding is load-bearing: one Slack install serves every Tenant.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
