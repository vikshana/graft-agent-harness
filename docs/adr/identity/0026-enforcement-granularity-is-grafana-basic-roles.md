---
id: ADR-0026
title: Enforcement granularity is Grafana basic roles
status: accepted
date: 2026-09-12
deciders: []
category: identity
tags: [identity, authn, authz]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/external-identity-mapping.md
legacy_id: D26
---

# ADR-0026 — Enforcement granularity is Grafana basic roles

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D26`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Custom-role (fine-grained action/scope) RBAC evaluation is Enterprise-only in Grafana OSS.** Confirmed live 2026-09-12: `POST /api/access-control/roles` 404s against Grafana OSS `latest`. This makes ADR-0023/ADR-0011's basic-role (Viewer/Editor/Admin) fallback the **only** available enforcement granularity in OSS, not merely a fallback for a hypothetical limitation.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
