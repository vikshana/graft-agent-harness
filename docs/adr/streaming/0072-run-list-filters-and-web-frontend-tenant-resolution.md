---
id: ADR-0072
title: Run list filters and web-frontend Tenant resolution
status: accepted
date: 2026-09-13
deciders: [ ]
category: streaming
tags: [ streaming, events ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ADR-0064 ]
design: ../../design/streaming-and-events.md
legacy_id: null
---

# ADR-0072 — Run list filters and web-frontend Tenant resolution

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D72`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

ADR-0064's original scope bundled run-list filtering and web-frontend Tenant resolution together with shared-run control
clauses. When ADR-0065 superseded ADR-0064's approval-related clause, the run-list and Tenant-resolution clauses needed
a home of their own, since they were never about run control and should not be entangled with a superseded decision.

## 2. Decision

**Run list filters are "Mine" and "Tenant"** — deliberately *not* the originally proposed "mine / my team / all",
because there is no "my team"
(Group is not a scoping layer, ADR-0051) and no "all" (cross-Tenant listing does not exist, ADR-0051).

**Web frontend (post-v1, ADR-0002): Tenant resolution is OIDC/SSO against the existing `graft_external_ref` mapping**
(ADR-0060) — an explicit Tenant switcher seeded from the Principal's `default_graft_tenant_id`, active Tenant carried in
the harness token exactly as every other surface. No new resolution mechanism is invented for it.

> Split out of legacy `ADR-0064` during the 2026-09-13 ADR migration:
> these clauses survived ADR-0065's supersession of ADR-0064's approval
> clause, and were never about run control in the first place.

## 3. Considered options

| Option                                                                                        | Verdict     | Why                                                                                                                                                                               |
|-----------------------------------------------------------------------------------------------|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Run-list filters: "mine / my team / all" (originally proposed)                                | ❌ Rejected | There is no "my team" (Group is not a scoping layer, ADR-0051) and no "all" (cross-Tenant listing does not exist, ADR-0051) — both describe scopes the scope model does not have. |
| Run-list filters: "Mine" and "Tenant"                                                         | ✅ Chosen   | The only two scopes that exist under ADR-0051's collapsed scope model.                                                                                                            |
| Invent a new Tenant-resolution mechanism specific to the web frontend                         | ❌ Rejected | Unnecessary — the existing `graft_external_ref` mapping (ADR-0060) and OIDC/SSO already serve this need.                                                                          |
| Web frontend Tenant resolution via OIDC/SSO against the existing `graft_external_ref` mapping | ✅ Chosen   | Reuses the same active-Tenant-in-token pattern every other surface already uses; seeded from the Principal's `default_graft_tenant_id`.                                           |

## 4. Consequences

- **Positive —** run-list filters and Tenant resolution both map cleanly onto scopes and mechanisms that already exist,
  with nothing new invented.
- **Negative / accepted trade —** none recorded beyond the scope limitations already implied by ADR-0051 (no "my team",
  no "all").
- **Follow-on work —** the web frontend's Tenant switcher must be seeded from `default_graft_tenant_id` and carry the
  active Tenant in the harness token exactly as every other surface does.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).
