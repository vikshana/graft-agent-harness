---
id: ADR-0028
title: Canonical Slack identity is keyed by slack_enterprise_id
status: accepted
date: 2026-09-12
deciders: [ ]
category: identity
tags: [ identity, authn, authz ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ADR-0052 ]
relates_to: [ ]
design: ../../design/external-identity-mapping.md
legacy_id: D28
---

# ADR-0028 — Canonical Slack identity is keyed by slack_enterprise_id

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D28`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

A Slack-linked Principal (ADR-0020) needs a canonical key. A single Slack workspace's `user_id` looked sufficient until
Enterprise Grid — where one human can hold several distinct per-workspace identities inside the same Grid organisation —
was checked directly against Slack's own platform behaviour.

## 2. Decision

**Canonical Slack identity keys Grid-linked principals by `slack_enterprise_id` (+ global user id)**, falling back to
`slack_workspace_id` (+ user id) for non-Grid, single-workspace installs. Confirmed necessary live against
`docs.slack.dev`, 2026-09-12: Enterprise Grid workspaces expose a constant `slack_enterprise_id`, and a single human can
hold **distinct per-workspace identities within the same Grid org**, reconciled by Slack via global user IDs —
`slack_workspace_id` alone is not a stable enough key once Grid is in play.

## 3. Considered options

| Option                                                                                                                                      | Verdict     | Why                                                                                                                                                                                 |
|---------------------------------------------------------------------------------------------------------------------------------------------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Key Grid-linked principals by `slack_enterprise_id` (+ global user id), fall back to `slack_workspace_id` (+ user id) for non-Grid installs | ✅ Chosen   | Confirmed live: Grid exposes a constant `slack_enterprise_id`, and only this key survives a human holding distinct per-workspace identities within the same Grid org                |
| Key canonical Slack identity by `slack_workspace_id` (+ user id) unconditionally                                                            | ❌ Rejected | Not stable once Enterprise Grid is in play — the same human can present different per-workspace identities inside one Grid org, so this key silently splits one person into several |

## 4. Consequences

- **Positive —** a single canonical key survives the Grid case instead of silently fragmenting one person's identity
  across workspaces; a Principal may legitimately hold several `slack_user_id` values under Grid (ADR-0060 section 4.4),
  and this decision is what makes that safe to model.
- **Negative / accepted trade —** two distinct keying schemes must be supported (Grid vs. non-Grid), rather than one
  uniform rule.
- **Follow-on work —** amended by ADR-0052, which folds this keying rule into the normative glossary's identity
  vocabulary.
- **Revisit trigger —** none observed.

## 5. Verification

- Verified live 2026-09-12 against `docs.slack.dev`: Enterprise Grid workspaces expose a constant `slack_enterprise_id`,
  and Slack reconciles per-workspace identities within a Grid org via global user IDs. Mechanism:
  [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

