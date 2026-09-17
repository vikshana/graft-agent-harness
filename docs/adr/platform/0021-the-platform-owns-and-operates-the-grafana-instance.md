---
id: ADR-0021
title: The platform owns and operates the Grafana instance
status: accepted
date: 2026-09-12
deciders: [ ]
category: platform
tags: [ platform, deployment ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/platform-topology.md
legacy_id: D21
---

# ADR-0021 — The platform owns and operates the Grafana instance

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D21`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/platform-topology.md`](../../design/platform-topology.md).

---

## 1. Context

The deployment/ownership model for the Grafana instance customers use needed fixing: customer-hosted (bring-your-own
Grafana) versus platform-hosted, and one Grafana instance per customer versus one shared instance with customers as orgs
within it.

## 2. Decision

**The platform owns and operates the Grafana instance; customers are orgs within a single shared instance** — confirmed,
not customer-hosted. Grafana runs **OSS**, at **latest release**.

## 3. Considered options

| Option                                                                                 | Verdict     | Why                                                                                                                                                                                                                                                                           |
|----------------------------------------------------------------------------------------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Customer-hosted Grafana (bring-your-own)                                               | ❌ Rejected | Confirmed against — the decision explicitly rules out customer-hosted.                                                                                                                                                                                                        |
| Platform-owned single shared instance, customers as GrafanaOrgs, OSS at latest release | ✅ Chosen   | Lets the platform rely on current-release Grafana behaviour (what makes ADR-0009's `X-Grafana-Id` identity forwarding safe), with Grafana OSS's basic-roles-only RBAC (ADR-0026) as a known, fixed constraint rather than one that varies per customer's self-hosted version. |

## 4. Consequences

- **Positive —** the platform can always rely on latest-release Grafana behaviour, with no fleet of customer-pinned old
  versions to support.
- **Negative / accepted trade —** Grafana OSS has no custom-role RBAC, so basic roles are the only available enforcement
  granularity (ADR-0026) — not a fallback, the only option OSS offers.
- **Follow-on work —** `grafana_org_id` is region-local, not global (ADR-0049, ADR-0060, `is_global = false`): org `5`
  in one region is a different Tenant than org `5` in the other.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/platform-topology.md`](../../design/platform-topology.md) section 1.
