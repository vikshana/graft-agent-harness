---
id: ADR-0060
title: External references are modelled in three layers
status: accepted
date: 2026-09-13
deciders: []
category: identity
tags: [identity, authn, authz]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/external-identity-mapping.md
legacy_id: D60
---

# ADR-0060 — External references are modelled in three layers

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D60`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**External references are modelled in three layers, not two — our key → our reference slot → their native field — held in a `graft_ref_kind` registry plus a `graft_external_ref` mapping table.** ADR-0059's prefix names *who owns the namespace*; it does not record *what that owner calls the field*, so `graft_ref_kind.native_field` does (`slack_workspace_id` → Slack's `team_id`, `grafana_org_id` → Grafana's `id`/`orgId`). The registry also carries **`is_stable`** and **`is_global`**, the two assumptions that cause outages when wrong and that otherwise live only in people's heads — `grafana_org_id` is `is_global = false`, so org `5` exists in *both* ADR-0049 regions meaning different Tenants. `graft_external_ref`'s **primary key is `(ref_kind, ref_scope, external_value)`**, i.e. the *inbound* direction, because every Slack event, Grafana request and webhook arrives carrying a foreign id that must resolve to a `graft_*` key before anything else happens — and including `ref_scope` makes the region-local trap **structurally impossible** rather than a thing to remember. `external_value` is stored **verbatim, never normalised** (normalising is how two distinct Principals silently merge). **Foreign ids are never a primary key of ours** and **email is never a join key** — it is mutable and reassignable, so matching on it makes an address reissued to a new hire a silent identity takeover, disqualifying under ADR-0015 and ADR-0025; the correct federated key is OIDC's `(iss, sub)` pair. `principal_identity` (ADR-0052) generalises into this table. **`dbos_workflow_id = graft_run_id`** — ADR-0042 makes it caller-supplied, so the value is ours; setting them equal stops drift and makes ADR-0042's idempotency key self-evident. **Verified 2026-09-13 against three primary sources:** RFC 7643 section 3.1 (SCIM `id` must be “stable, non-reassignable”; `externalId` exists explicitly to avoid storing a local mapping — an escape hatch unavailable to us, since Grafana and Slack will not accept a `graft_tenant_id`), Backstage well-known annotations (own key is `entityRef`; foreign ids are annotations namespaced by DNS domain — `github.com/project-slug` — named in the foreign system's *own* vocabulary), and incident.io's catalog-importer config reference (`external_id` for identity plus a separate **`sync_id`** provenance marker governing what a sync may delete).

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
