---
id: ADR-0072
title: Run list filters and web-frontend Tenant resolution
status: accepted
date: 2026-09-13
deciders: []
category: streaming
tags: [streaming, events]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: [ADR-0064]
design: ../../design/streaming-and-events.md
legacy_id: null
---

# ADR-0072 — Run list filters and web-frontend Tenant resolution

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D72`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Run list filters are “Mine” and “Tenant”** — deliberately *not* the originally proposed “mine / my team / all”, because there is no “my team” (Group is not a scoping layer, ADR-0051) and no “all” (cross-Tenant listing does not exist, ADR-0051).

**Web frontend (post-v1, ADR-0002): Tenant resolution is OIDC/SSO against the existing `graft_external_ref` mapping** (ADR-0060) — an explicit Tenant switcher seeded from the Principal's `default_graft_tenant_id`, active Tenant carried in the harness token exactly as every other surface. No new resolution mechanism is invented for it.

> Split out of legacy `ADR-0064` during the 2026-09-13 ADR migration: these clauses survived ADR-0065's supersession of ADR-0064's approval clause, and were never about run control in the first place.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
