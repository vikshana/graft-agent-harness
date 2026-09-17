---
id: ADR-0051
title: The scope model collapses to a single graft_tenant_id
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
legacy_id: D51
---

# ADR-0051 — The scope model collapses to a single graft_tenant_id

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D51`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).

---

## 1. Context

An earlier scope model (R3) proposed a `Tenant → Workspace → Group →
Principal` tree, assuming Tenant and Workspace were distinct scoping
layers. In practice, Workspace was always 1:1 with a GrafanaOrg, which is
1:1 with a customer team — exactly what `tenant_id` already identified.
Two keys for the same concept is a standing isolation-bug source enforced
by nothing, and needed resolving before more of the design was built on
top of the four-layer tree.

## 2. Decision

**The scope model collapses to a single layer: `graft_tenant_id`.
`workspace_id` is deleted and "Workspace" is removed from the vocabulary
entirely.** R3's `Tenant → Workspace → Group → Principal` tree assumed
Tenant and Workspace were distinct; they are not — Workspace was 1:1 with
a GrafanaOrg, which is 1:1 with a customer team, which is what
`tenant_id` already identified. Two keys for one concept is a standing
isolation-bug source enforced by nothing. **Tenant ≡ GrafanaOrg, 1:1.**
The Grafana `grafana_org_id` is a **mapped attribute, not the key** — it
is a region-local integer assigned by Grafana and collides across the two
ADR-0049 deployments. **Collapsing is the reversible direction:** adding a
billing parent above Tenant later is a new table and a join; adding a
scoping key *below* every row is the expensive rewrite R3 rightly feared.
**Group and Principal are authorisation and identity, not scoping.**
Tenant resolution per surface: Grafana **follows the active GrafanaOrg**
(that surface contains no resolution logic at all); Slack uses
admin-configured **SlackChannel→Tenant binding** for channels and a
per-Principal default Tenant for DMs, asking only as a fallback; webhooks
derive it from the alert's source GrafanaOrg. **No cross-Tenant Runs in
v1** — the workaround is two Runs, and there is no audited exception to
build or to get wrong. **All prior uses of "workspace"/`workspace_id` in
ADR-0016, ADR-0017, ADR-0018, ADR-0031, ADR-0044 and elsewhere read as
Tenant/`graft_tenant_id`.**

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Keep the four-layer `Tenant → Workspace → Group → Principal` tree (R3) | ❌ Rejected | Workspace was always 1:1 with a GrafanaOrg, which is what `tenant_id` already identified — two keys for one concept, enforced by nothing, a standing isolation-bug source. |
| Collapse Tenant and Workspace into a single `graft_tenant_id` scoping layer, with Group and Principal reclassified as authorisation/identity, not scoping | ✅ Chosen | Removes the redundant key; collapsing is the reversible direction (adding a billing parent above Tenant later is cheap; adding a scoping key below every row later is the expensive rewrite this avoids). |
| Allow cross-Tenant Runs, with an audited exception mechanism | ❌ Rejected | No audited exception to build or to get wrong — the workaround (two separate Runs) is simpler and has no exception surface at all. |

## 4. Consequences

- **Positive —** a single scoping key (`graft_tenant_id`) removes an
  entire class of isolation bugs from having two keys for one concept;
  `grafana_org_id` is correctly demoted to a mapped, region-local
  attribute rather than treated as a key.
- **Negative / accepted trade —** every prior ADR and design reference to
  "workspace"/`workspace_id` must now be read as Tenant/`graft_tenant_id`
  — a vocabulary migration across the existing decision set.
- **Follow-on work —** each surface needs its own Tenant-resolution rule:
  Grafana follows the active GrafanaOrg, Slack uses SlackChannel→Tenant
  binding (with a per-Principal default for DMs), webhooks derive it from
  the alert's source GrafanaOrg.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).
