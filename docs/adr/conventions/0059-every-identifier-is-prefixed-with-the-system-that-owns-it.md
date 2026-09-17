---
id: ADR-0059
title: Every identifier is prefixed with the system that owns it
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
legacy_id: D59
---

# ADR-0059 — Every identifier is prefixed with the system that owns it

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D59`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../GLOSSARY.md`](../../GLOSSARY.md).

---

## 1. Context

ADR-0052 fixed the vocabulary for terms like tenant/org/workspace, but identifiers themselves (the actual ID columns and
fields flowing through schemas, claims, headers and telemetry) still needed a rule for which system owns which ID, and
how to tell at a glance whether a given identifier is ours to guarantee or merely stored on behalf of another system.

## 2. Decision

**Every identifier is prefixed with the system that owns it.** `graft_*`
means we mint it, own the format, guarantee uniqueness and control its lifetime; `grafana_*`, `slack_*`, `idp_*`,
`dbos_*`, `lgtm_*`, `github_*`,
`jira_*`, `k8s_*` mean somebody else mints it — we store it, may match on it, and guarantee **nothing** about it. **An
unprefixed identifier in new code or documents is a review defect.** Concretely: `graft_tenant_id`,
`graft_principal_id`, `graft_run_id`, `graft_event_id`, `graft_role_id`,
`graft_connection_id`, `graft_schedule_id`; and `grafana_org_id`,
`slack_enterprise_id`, `slack_workspace_id` (Slack's `team_id`, named for what Slack's UI calls it), `slack_channel_id`,
`slack_user_id`,
`dbos_workflow_id`, `lgtm_tenant_id`. **The prefix is fixed; the separator follows the medium** — `snake_case` in
SQL/JSON/claims, dotted in OTel (`graft.tenant.id`), `X-Graft-*` in HTTP headers, and a `graft.` GUC namespace for RLS
(`SET LOCAL graft.tenant_id`, replacing the earlier
`app.` namespace). Four deliberate exceptions: URL path parameters (positional, already unambiguous); role-named foreign
keys (`run.initiator_id`); `principal_identity.external_id` (polymorphic — its owner is the sibling `provider` column);
and **prose quoting an external API, which keeps that API's native spelling** (a sentence about what Slack returns says
`team_id`, because renaming it there would misdescribe the API — the prefixed form is for *our* schema, claims and
attributes). **This pays off directly at two boundaries already locked:** ADR-0015 propagates
`graft_run_id` *outward* into customer-owned logs, where an unprefixed
`run_id` would be ambiguous in the customer's own log stream; and
`lgtm_tenant_id` vs `graft_tenant_id` is exactly the collision ADR-0052 was written to stop. **All prior decisions'
unprefixed identifiers read as their prefixed form.**

## 3. Considered options

| Option                                                                                                                                                 | Verdict     | Why                                                                                                                                                                                                                                          |
|--------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Leave identifiers unprefixed, disambiguated by field name and surrounding schema context                                                               | ❌ Rejected | Fails exactly where it matters most: `graft_run_id` propagated outward into a customer's own log stream would be ambiguous as a bare `run_id`, and `lgtm_tenant_id` vs `graft_tenant_id` is precisely the collision ADR-0052 exists to stop. |
| Prefix every identifier with the system that owns and mints it (`graft_*` for ours, `grafana_*`/`slack_*`/etc. for others), with four named exceptions | ✅ Chosen   | Makes ownership and guarantee level legible from the name alone, at every boundary — schema, claims, headers, telemetry, and customer-facing logs.                                                                                           |

## 4. Consequences

- **Positive —** ownership and guarantee level (do we mint it, or just store it) is legible from the identifier name
  alone, across SQL, JSON, claims, OTel spans, HTTP headers and RLS GUCs.
- **Negative / accepted trade —** four deliberate exceptions (URL path parameters, role-named foreign keys,
  `principal_identity.external_id`, and prose quoting an external API) must be remembered and applied consistently
  rather than mechanically prefixing everything.
- **Follow-on work —** an unprefixed identifier in new code or documents is a review defect; all prior decisions'
  unprefixed identifiers must be read as their prefixed form going forward.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../GLOSSARY.md`](../../GLOSSARY.md).
