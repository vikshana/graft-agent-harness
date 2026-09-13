---
id: ADR-0017
title: Limits form a ceiling chain
status: accepted
date: 2026-09-12
deciders: []
category: tenancy
tags: [tenancy, scoping, rbac]
supersedes: []
superseded_by: []
amends: []
amended_by: [ADR-0057]
relates_to: []
design: ../../design/tenancy-and-scoping.md
legacy_id: D17
---

# ADR-0017 — Limits form a ceiling chain

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D17`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Limits form a ceiling chain** — `platform ≥ tenant ≥ workspace ≥ user ≥ run`, effective limit is the minimum across scopes. Platform ceilings are **not customer-raisable**. Per-connection throttles (protecting *customer* infrastructure, e.g. a shared K8s control plane) are keyed by connection, independent of workspace quota.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
