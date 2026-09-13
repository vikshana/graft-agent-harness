---
id: ADR-0059
title: Every identifier is prefixed with the system that owns it
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
legacy_id: D59
---

# ADR-0059 — Every identifier is prefixed with the system that owns it

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D59`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../GLOSSARY.md`](../../GLOSSARY.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Every identifier is prefixed with the system that owns it.** `graft_*` means we mint it, own the format, guarantee uniqueness and control its lifetime; `grafana_*`, `slack_*`, `idp_*`, `dbos_*`, `lgtm_*`, `github_*`, `jira_*`, `k8s_*` mean somebody else mints it — we store it, may match on it, and guarantee **nothing** about it. **An unprefixed identifier in new code or documents is a review defect.** Concretely: `graft_tenant_id`, `graft_principal_id`, `graft_run_id`, `graft_event_id`, `graft_role_id`, `graft_connection_id`, `graft_schedule_id`; and `grafana_org_id`, `slack_enterprise_id`, `slack_workspace_id` (Slack's `team_id`, named for what Slack's UI calls it), `slack_channel_id`, `slack_user_id`, `dbos_workflow_id`, `lgtm_tenant_id`. **The prefix is fixed; the separator follows the medium** — `snake_case` in SQL/JSON/claims, dotted in OTel (`graft.tenant.id`), `X-Graft-*` in HTTP headers, and a `graft.` GUC namespace for RLS (`SET LOCAL graft.tenant_id`, replacing the earlier `app.` namespace). Four deliberate exceptions: URL path parameters (positional, already unambiguous); role-named foreign keys (`run.initiator_id`); `principal_identity.external_id` (polymorphic — its owner is the sibling `provider` column); and **prose quoting an external API, which keeps that API's native spelling** (a sentence about what Slack returns says `team_id`, because renaming it there would misdescribe the API — the prefixed form is for *our* schema, claims and attributes). **This pays off directly at two boundaries already locked:** ADR-0015 propagates `graft_run_id` *outward* into customer-owned logs, where an unprefixed `run_id` would be ambiguous in the customer's own log stream; and `lgtm_tenant_id` vs `graft_tenant_id` is exactly the collision ADR-0052 was written to stop. **All prior decisions' unprefixed identifiers read as their prefixed form.**

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
