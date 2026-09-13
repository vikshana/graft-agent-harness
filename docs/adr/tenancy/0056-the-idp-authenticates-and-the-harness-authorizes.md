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

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**The IdP authenticates; the harness authorises.** The IdP establishes only *who the Principal is*. Role assignment, permission verbs and evaluation live entirely in our own tables — satisfying the explicit IdP-independence requirement (Entra/Keycloak/Auth0/AD interchangeable, zero code change) and sidestepping ADR-0026's finding that fine-grained RBAC is Grafana-Enterprise-only. **Four roles: `platform_admin` (← GrafanaServerAdmin), `tenant_admin` (← GrafanaOrgAdmin), `responder` (← Grafana Editor), `viewer` (← Grafana Viewer).** **A fifth proposed role, `operator`, was surfaced as a contradiction and deleted**: a separate approve-granting role deadlocked against ADR-0055 — an Editor-mapped member could start a Run whose proposed action *nobody* could approve (not them, wrong role; not anyone else, initiator-only). Approval authority is instead resolved **per action at call time by ADR-0023**, which is exactly ADR-0016's “per-user variation is an authorisation filter at call time.” **Non-Grafana write classes** (K8s, GitHub, Jira) have no Grafana permission to check, so their **required Role is declared in the tool policy (ADR-0016), defaulting to `tenant_admin`**. Resolution order: explicit Group→Role mapping → explicit per-Principal grant → **zero-config default derived from the live Grafana basic role** (computed at token-mint time, never stored, so it cannot go stale) — the last being what makes brownfield viable, since hundreds of Tenants cannot each require manual mapping before first use. The call-time Grafana check is **not a role source**: it is an independent ceiling, so our Role can never permit what Grafana would refuse (ADR-0024's Slack/`system_initiated` exemption stands). **Roles and verbs are rows, not code** — extensible by data change plus a ADR-0016 policy version bump. **De-provisioning is TTL-only** (~10 min, ADR-0010) with the existing deny-list for incidents; no SCIM, no polling.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
