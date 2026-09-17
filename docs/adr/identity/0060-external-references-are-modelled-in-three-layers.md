---
id: ADR-0060
title: External references are modelled in three layers
status: accepted
date: 2026-09-13
deciders: [ ]
category: identity
tags: [ identity, authn, authz ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/external-identity-mapping.md
legacy_id: D60
---

# ADR-0060 — External references are modelled in three layers

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D60`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

ADR-0059 fixed identifier *prefixes*, but a prefix alone still conflates two different things: our own name for a
reference slot, and the external system's own name for that field in its own API. That conflation is what produces the
concrete bug of someone grepping a captured payload for our internal name and finding nothing, wrongly concluding an
integration is broken. A model was needed that keeps "ours" and "theirs" separate, and that makes the region-local id
trap (the same numeric Grafana org id existing in two regions, ADR-0049, meaning two different Tenants)
structurally impossible rather than a fact people have to remember.

## 2. Decision

**External references are modelled in three layers, not two — our key → our reference slot → their native field — held
in a `graft_ref_kind` registry plus a `graft_external_ref` mapping table.** ADR-0059's prefix names *who owns the
namespace*; it does not record *what that owner calls the field*, so `graft_ref_kind.native_field` does
(`slack_workspace_id` → Slack's `team_id`, `grafana_org_id` → Grafana's `id`/`orgId`). The registry also carries **
`is_stable`** and **`is_global`**, the two assumptions that cause outages when wrong and that otherwise live only in
people's heads — `grafana_org_id` is `is_global = false`, so org `5` exists in *both* ADR-0049 regions meaning different
Tenants. `graft_external_ref`'s **primary key is `(ref_kind, ref_scope, external_value)`**, i.e. the *inbound*
direction, because every Slack event, Grafana request and webhook arrives carrying a foreign id that must resolve to a
`graft_*` key before anything else happens — and including `ref_scope` makes the region-local trap **structurally
impossible** rather than a thing to remember. `external_value` is stored **verbatim, never normalised** (normalising is
how two distinct Principals silently merge). **Foreign ids are never a primary key of ours** and **email is never a join
key** — it is mutable and reassignable, so matching on it makes an address reissued to a new hire a silent identity
takeover, disqualifying under ADR-0015 and ADR-0025; the correct federated key is OIDC's `(iss, sub)` pair.
`principal_identity` (ADR-0052) generalises into this table. **`dbos_workflow_id = graft_run_id`** — ADR-0042 makes it
caller-supplied, so the value is ours; setting them equal stops drift and makes ADR-0042's idempotency key self-evident.
**Verified 2026-09-13 against three primary sources:** RFC 7643 section 3.1 (SCIM `id` must be “stable,
non-reassignable”; `externalId` exists explicitly to avoid storing a local mapping — an escape hatch unavailable to us,
since Grafana and Slack will not accept a `graft_tenant_id`), Backstage well-known annotations (own key is `entityRef`;
foreign ids are annotations namespaced by DNS domain — `github.com/project-slug` — named in the foreign system's *own*
vocabulary), and incident.io's catalog-importer config reference (`external_id` for identity plus a separate **
`sync_id`** provenance marker governing what a sync may delete).

## 3. Considered options

| Option                                                                                                                                                                           | Verdict     | Why                                                                                                                                                                                                           |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Three layers — our key → our reference slot → their native field — held in a `graft_ref_kind` registry plus a `graft_external_ref` mapping table, keyed on the inbound direction | ✅ Chosen   | Separates "our slot name" from "their field name" explicitly; `is_stable`/`is_global` flags make the region-local trap structurally impossible; verified against SCIM, Backstage and incident.io as precedent |
| Keep the existing two-layer model (prefix + raw value only)                                                                                                                      | ❌ Rejected | The conflation of layers 2 and 3 is the root cause of the grep-and-conclude-it's-broken bug this decision fixes                                                                                               |
| Rely on the external system's own `externalId`/annotation mechanism instead of our own mapping table                                                                             | ❌ Rejected | Grafana and Slack do not accept a `graft_tenant_id` we hand them, so SCIM's `externalId` escape hatch (storing the mapping on their side) is unavailable to us — we must store the local mapping ourselves    |

## 4. Consequences

- **Positive —** `principal_identity` (ADR-0052) generalises into one mechanism (`graft_external_ref`); the region-local
  trap is closed by schema (`ref_scope` in the primary key), not by convention;
  `dbos_workflow_id = graft_run_id` removes a whole class of drift.
- **Negative / accepted trade —** two new tables and a registry to maintain, and every new external system integrated
  must add a
  `graft_ref_kind` row before its ids can be looked up safely.
- **Follow-on work —** verify Layer-3 field names against live captured payloads (currently populated from documentation
  and prior sessions, not captured traffic); design a re-link path for Slack Grid migration, where
  `slack_user_id` changes shape.
- **Revisit trigger —** none observed beyond the open items above.

## 5. Verification

- Verified 2026-09-13 against three primary sources: RFC 7643 section 3.1 (SCIM `id`/`externalId`), Backstage's
  well-known-annotations convention, and incident.io's catalog-importer config reference (`external_id`/`sync_id`).
  Mechanism:
  [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md)
  sections 1–3.

