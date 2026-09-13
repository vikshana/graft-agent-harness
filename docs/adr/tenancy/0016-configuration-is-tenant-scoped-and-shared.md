---
id: ADR-0016
title: Configuration is Tenant-scoped and shared
status: accepted
date: 2026-09-12
deciders: []
category: tenancy
tags: [tenancy, scoping, rbac]
supersedes: []
superseded_by: []
amends: []
amended_by: [ADR-0062]
relates_to: []
design: ../../design/tenancy-and-scoping.md
legacy_id: D16
---

# ADR-0016 — Configuration is Tenant-scoped and shared

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D16`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Configuration is org-scoped and shared** (workspace = Grafana Org); per-user variation is an **authorisation filter at call time**, never a separate per-user configuration. Enabling a write-capable tool class requires a step-up (re-authenticated) action distinct from ordinary config edits, and is itself an audit record. Tool policy is **versioned, never overwritten**.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
