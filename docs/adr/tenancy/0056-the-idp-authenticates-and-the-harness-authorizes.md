---
id: ADR-0056
title: The IdP authenticates and the harness authorises
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
legacy_id: D56
---

# ADR-0056 — The IdP authenticates and the harness authorises

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D56`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).

---

## 1. Context

The platform must support customers on different identity providers
(Entra, Keycloak, Auth0, AD) without per-IdP code changes, and Grafana OSS
lacks fine-grained RBAC (ADR-0026 already found custom-role RBAC is
Grafana-Enterprise-only). A role model was needed that is IdP-independent
and works within Grafana OSS's basic roles, along with a way to resolve
roles for non-Grafana tool classes (K8s, GitHub, Jira) that have no
Grafana permission to check against.

## 2. Decision

**The IdP authenticates; the harness authorises.** The IdP establishes
only *who the Principal is*. Role assignment, permission verbs and
evaluation live entirely in our own tables — satisfying the explicit
IdP-independence requirement (Entra/Keycloak/Auth0/AD interchangeable,
zero code change) and sidestepping ADR-0026's finding that fine-grained
RBAC is Grafana-Enterprise-only. **Four roles: `platform_admin` (←
GrafanaServerAdmin), `tenant_admin` (← GrafanaOrgAdmin), `responder` (←
Grafana Editor), `viewer` (← Grafana Viewer).** **A fifth proposed role,
`operator`, was surfaced as a contradiction and deleted**: a separate
approve-granting role deadlocked against ADR-0055 — an Editor-mapped
member could start a Run whose proposed action *nobody* could approve
(not them, wrong role; not anyone else, initiator-only). Approval
authority is instead resolved **per action at call time by ADR-0023**,
which is exactly ADR-0016's "per-user variation is an authorisation
filter at call time." **Non-Grafana write classes** (K8s, GitHub, Jira)
have no Grafana permission to check, so their **required Role is declared
in the tool policy (ADR-0016), defaulting to `tenant_admin`**. Resolution
order: explicit Group→Role mapping → explicit per-Principal grant →
**zero-config default derived from the live Grafana basic role** (computed
at token-mint time, never stored, so it cannot go stale) — the last being
what makes brownfield viable, since hundreds of Tenants cannot each
require manual mapping before first use. The call-time Grafana check is
**not a role source**: it is an independent ceiling, so our Role can never
permit what Grafana would refuse (ADR-0024's Slack/`system_initiated`
exemption stands). **Roles and verbs are rows, not code** — extensible by
data change plus a ADR-0016 policy version bump. **De-provisioning is
TTL-only** (~10 min, ADR-0010) with the existing deny-list for incidents;
no SCIM, no polling.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Let the IdP's own role/group claims drive authorisation directly | ❌ Rejected | Would tie authorisation logic to whichever IdP a customer uses, breaking the explicit IdP-independence requirement (Entra/Keycloak/Auth0/AD interchangeable, zero code change). |
| Rely on Grafana Enterprise's fine-grained RBAC | ❌ Rejected | ADR-0026 already found fine-grained RBAC is Grafana-Enterprise-only; the platform targets Grafana OSS (ADR-0021). |
| Add a fifth role, `operator`, with dedicated approve authority | ❌ Rejected | Deadlocked against ADR-0055 — an Editor-mapped member could start a Run whose proposed action nobody could approve; deleted, with approval resolved per action at call time instead. |
| Four roles (`platform_admin`/`tenant_admin`/`responder`/`viewer`) mapped from Grafana basic roles, computed at token-mint time from the live Grafana role | ✅ Chosen | IdP-independent, works within Grafana OSS's basic-role ceiling, and the zero-config default makes brownfield onboarding viable without per-Tenant manual mapping. |

## 4. Consequences

- **Positive —** the platform is genuinely IdP-independent, and hundreds
  of brownfield Tenants get a working zero-config Role default without
  manual mapping.
- **Negative / accepted trade —** de-provisioning is TTL-only (~10 min)
  rather than instant via SCIM/polling — accepted alongside the existing
  deny-list for incidents.
- **Follow-on work —** roles and verbs are data rows, extensible by a
  ADR-0016 policy version bump rather than a code change; non-Grafana
  write classes must declare their required Role in tool policy,
  defaulting to `tenant_admin`.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).
