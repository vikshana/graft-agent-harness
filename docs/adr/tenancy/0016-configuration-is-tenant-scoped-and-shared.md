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

Tool and behaviour configuration needed a scoping model: per-user
configuration is tempting (it feels natural to let each user tune their
own experience), but it multiplies the surface that must be audited and
kept consistent, and a write-capable tool class being enabled quietly by
one user's preference would be a policy change hiding as a personal
setting.

## 2. Decision

**Configuration is org-scoped and shared** (workspace = Grafana Org);
per-user variation is an **authorisation filter at call time**, never a
separate per-user configuration. Enabling a write-capable tool class
requires a step-up (re-authenticated) action distinct from ordinary
config edits, and is itself an audit record. Tool policy is **versioned,
never overwritten**.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Per-user configuration (each Principal tunes their own tool/behaviour settings) | ❌ Rejected | Multiplies the audited surface and lets a policy change (e.g. enabling a write-capable tool class) hide as a personal preference rather than a reviewable act. |
| Tenant-scoped, shared configuration; per-user variation resolved as an authorisation filter at call time | ✅ Chosen | Keeps configuration itself auditable and shared, while still letting different Principals have different effective capability via call-time authorisation rather than divergent stored config. |

## 4. Consequences

- **Positive —** configuration stays auditable and consistent across a
  Tenant; enabling a write-capable tool class is always a distinct,
  audited, step-up action rather than an incidental personal setting.
- **Negative / accepted trade —** tool policy is versioned rather than
  freely editable, meaning every change is a recorded version bump, not
  an in-place edit.
- **Follow-on work —** amended by ADR-0062, which narrows this ADR to
  govern *capability* only, introducing custom instructions (which govern
  *behaviour*) at both Tenant and Principal level without reopening
  per-user configuration of capability.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).
