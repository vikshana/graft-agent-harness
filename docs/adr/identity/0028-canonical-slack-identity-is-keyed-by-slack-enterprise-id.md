---
id: ADR-0028
title: Canonical Slack identity is keyed by slack_enterprise_id
status: accepted
date: 2026-09-12
deciders: []
category: identity
tags: [identity, authn, authz]
supersedes: []
superseded_by: []
amends: []
amended_by: [ADR-0052]
relates_to: []
design: ../../design/external-identity-mapping.md
legacy_id: D28
---

# ADR-0028 — Canonical Slack identity is keyed by slack_enterprise_id

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D28`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Canonical Slack identity keys Grid-linked principals by `slack_enterprise_id` (+ global user id)**, falling back to `slack_workspace_id` (+ user id) for non-Grid, single-workspace installs. Confirmed necessary live against `docs.slack.dev`, 2026-09-12: Enterprise Grid workspaces expose a constant `slack_enterprise_id`, and a single human can hold **distinct per-workspace identities within the same Grid org**, reconciled by Slack via global user IDs — `slack_workspace_id` alone is not a stable enough key once Grid is in play.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
