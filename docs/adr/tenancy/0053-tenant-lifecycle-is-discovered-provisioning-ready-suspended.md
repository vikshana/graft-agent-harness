---
id: ADR-0053
title: Tenant lifecycle is discovered, provisioning, ready, suspended
status: accepted
date: 2026-09-13
deciders: []
category: tenancy
tags: [tenancy, scoping, rbac]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/tenancy-and-scoping.md
legacy_id: D53
---

# ADR-0053 — Tenant lifecycle is discovered, provisioning, ready, suspended

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D53`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).

---

## 1. Context

ADR-0022 established synchronous service-account provisioning at Tenant
creation, but the platform must also onboard hundreds of pre-existing
GrafanaOrgs that never went through that creation flow. Provisioning
credentials for all of them up front would mean holding hundreds of
service-account tokens nobody has asked to use yet; a lifecycle model was
needed that reconciles brownfield backfill with ADR-0022's synchronous
flow, and that keeps platform-owned service accounts consistent even
though Grafana OSS lets a GrafanaOrgAdmin edit or delete them directly.

## 2. Decision

**Tenant lifecycle `discovered → provisioning → ready → suspended`,
reconciling ADR-0022's synchronous provisioning with hundreds of
pre-existing GrafanaOrgs.** A reconciler creates a **credential-less
`discovered` row for every existing GrafanaOrg** — free, no service
accounts, no cost — so the capability is one admin action away for every
team. **`discovered → ready` is the explicit admin act that fires
ADR-0022's synchronous SA provisioning**, so ADR-0022 is untouched *and*
we never hold hundreds of unused credentials. **One idempotent code
path** serves both backfill and new-org creation; no special-case
migration script. `suspended` revokes tokens and rejects new Runs without
deleting history. **Platform-owned SAs: naming is a signal, reconciliation
is the control** — Grafana OSS cannot prevent a GrafanaOrgAdmin editing or
deleting them. Reserved prefix `graft-platform-`
(`graft-platform-enforcement`, `graft-platform-mcp`) with a "Managed by
the Graft platform — do not modify" display name; a **drift reconciler**
(scheduled DBOS workflow, ADR-0047) asserts SA existence, minimum role
(ADR-0022) and token validity, re-provisioning and auditing on
divergence; **rotation is a scheduled workflow, not a calendar reminder**;
per-SA metrics: token age, time-to-expiry, last successful use, drift
events, re-provisions, reconciler lag.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Provision service-account credentials up front for every pre-existing GrafanaOrg | ❌ Rejected | Would mean holding hundreds of unused credentials for teams that never asked to use the capability. |
| A special-case backfill migration script, separate from the ADR-0022 new-Tenant creation path | ❌ Rejected | Two code paths for the same outcome (a Tenant reaching `ready`) is unnecessary; one idempotent path serves both. |
| Rely on Grafana OSS to prevent a GrafanaOrgAdmin from editing/deleting platform-owned service accounts | ❌ Rejected | Grafana OSS has no mechanism to prevent this; the mitigation must instead be detection and correction (naming convention plus a drift reconciler), not prevention. |
| Four-state lifecycle (`discovered → provisioning → ready → suspended`), with a scheduled drift reconciler and rotation workflow for platform-owned SAs | ✅ Chosen | Reconciles brownfield backfill with ADR-0022's synchronous flow via one idempotent code path, and detects/corrects SA drift since prevention isn't available in Grafana OSS. |

## 4. Consequences

- **Positive —** every pre-existing GrafanaOrg gets a free, credential-less
  `discovered` row, making the capability one admin action away without
  ever holding unused credentials; one idempotent code path serves both
  backfill and new-Tenant creation.
- **Negative / accepted trade —** platform-owned service accounts cannot be
  technically protected from GrafanaOrgAdmin edits/deletion in Grafana
  OSS — the mitigation is a scheduled drift reconciler that detects and
  corrects divergence, not a preventive control.
- **Follow-on work —** rotation is itself a scheduled workflow (not a
  calendar reminder), with per-SA metrics (token age, time-to-expiry,
  last successful use, drift events, re-provisions, reconciler lag) to
  monitor.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).
