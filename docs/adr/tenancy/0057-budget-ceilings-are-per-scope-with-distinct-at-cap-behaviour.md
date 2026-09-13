---
id: ADR-0057
title: Budget ceilings are per-scope with distinct at-cap behaviour
status: accepted
date: 2026-09-13
deciders: []
category: tenancy
tags: [tenancy, scoping, rbac]
supersedes: []
superseded_by: []
amends: [ADR-0017]
amended_by: []
relates_to: []
design: ../../design/tenancy-and-scoping.md
legacy_id: D57
---

# ADR-0057 — Budget ceilings are per-scope with distinct at-cap behaviour

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D57`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Budget enforcement: the ADR-0017 ceiling chain loses a layer — `platform ≥ tenant ≥ principal ≥ run`** — and at-cap behaviour is **deliberately per-scope, not uniform**: **per-run** (tokens, cost, graph depth, wall clock) → **graceful terminate**, emitting the best hypothesis formed so far plus `budget_consumed` (ADR-0029), never a bare failure; **per-principal** and **per-tenant** (monthly) → **hard stop**, new Runs rejected while in-flight Runs finish; **per-connection** → **throttle/queue**, never failing the Run outright, since it protects *customer* infrastructure and remains independent of Tenant quota (ADR-0044). **No degrade-to-a-cheaper-model** — model selection is a platform decision driven by evals and availability, and switching mid-Run would silently change the quality characteristics an operator is about to act on. **Monthly reset.** Quotas are platform-set and platform-customisable per Principal and per Tenant (not self-service); `tenant_admin` and `responder` **request increases from the UI**, creating an idempotency-keyed service-desk ticket pre-filled with `graft_tenant_id`, current ceiling, observed consumption and the triggering `graft_run_id`, applied by a `platform_admin` as an audited policy version bump (fallback: a deep link carrying the same context). **In-product quota indicator** per Principal and per Tenant, **threshold notification** (proposed 80%) via ADR-0035's path, and **platform monitoring** of consumption vs ceiling, at-cap rejection rate, and quota-request rate and time-to-fulfil.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
