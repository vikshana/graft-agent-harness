---
id: ADR-0026
title: Enforcement granularity is Grafana basic roles
status: accepted
date: 2026-09-12
deciders: [ ]
category: identity
tags: [ identity, authn, authz ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/external-identity-mapping.md
legacy_id: D26
---

# ADR-0026 — Enforcement granularity is Grafana basic roles

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D26`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

Check-then-act (ADR-0023) needs an enforcement granularity to evaluate against — fine-grained custom action/scope roles,
or Grafana's built-in basic roles (Viewer/Editor/Admin). Custom RBAC roles were assumed to be a possible
fallback-avoidance path until tested directly against a running instance.

## 2. Decision

**Custom-role (fine-grained action/scope) RBAC evaluation is Enterprise-only in Grafana OSS.** Confirmed live
2026-09-12: `POST /api/access-control/roles` 404s against Grafana OSS `latest`. This makes ADR-0023/ADR-0011's
basic-role (Viewer/Editor/Admin) fallback the **only** available enforcement granularity in OSS, not merely a fallback
for a hypothetical limitation.

## 3. Considered options

| Option                                                   | Verdict     | Why                                                                                                       |
|----------------------------------------------------------|-------------|-----------------------------------------------------------------------------------------------------------|
| Basic-role (Viewer/Editor/Admin) enforcement granularity | ✅ Chosen   | Confirmed the only option available in Grafana OSS; works identically regardless of customer license tier |
| Custom, fine-grained action/scope RBAC roles             | ❌ Rejected | Confirmed Enterprise-only: `POST /api/access-control/roles` returns 404 against Grafana OSS `latest`      |

## 4. Consequences

- **Positive —** one enforcement granularity works across every customer regardless of Grafana license tier, with no
  Enterprise-only code path to maintain for v1.
- **Negative / accepted trade —** check-then-act narrowing is coarser than fine-grained custom RBAC would allow
  (ADR-0011, ADR-0023) — a Viewer and a user with a narrowly scoped custom role are indistinguishable to this
  enforcement layer.
- **Follow-on work —** none for v1; a future Enterprise-only capability could layer finer-grained checks on top without
  changing the OSS baseline.
- **Revisit trigger —** Grafana OSS ships fine-grained custom-role evaluation, or the customer base moves predominantly
  to Enterprise.

## 5. Verification

- Confirmed live 2026-09-12 against Grafana OSS `latest`:
  `POST /api/access-control/roles` returns 404. Mechanism:
  [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md)
  and
  [`../../design/grafana-authz-delegation.md`](../../design/grafana-authz-delegation.md)
  section 5 item 2.

