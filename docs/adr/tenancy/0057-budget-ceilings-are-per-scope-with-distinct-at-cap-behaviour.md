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

ADR-0017's ceiling chain needed refining after ADR-0051 collapsed the
scope model (dropping the workspace layer), and a uniform "at cap, stop
everything" behaviour would be wrong for every scope alike: a per-run cap
should not fail a run outright when it can instead wrap up gracefully, but
a per-tenant monthly cap genuinely should stop new work. A path for
requesting quota increases, and a stance on "degrade to a cheaper model"
as a budget-relief mechanism, both needed settling too.

## 2. Decision

**Budget enforcement: the ADR-0017 ceiling chain loses a layer —
`platform ≥ tenant ≥ principal ≥ run`** — and at-cap behaviour is
**deliberately per-scope, not uniform**: **per-run** (tokens, cost, graph
depth, wall clock) → **graceful terminate**, emitting the best hypothesis
formed so far plus `budget_consumed` (ADR-0029), never a bare failure;
**per-principal** and **per-tenant** (monthly) → **hard stop**, new Runs
rejected while in-flight Runs finish; **per-connection** →
**throttle/queue**, never failing the Run outright, since it protects
*customer* infrastructure and remains independent of Tenant quota
(ADR-0044). **No degrade-to-a-cheaper-model** — model selection is a
platform decision driven by evals and availability, and switching
mid-Run would silently change the quality characteristics an operator is
about to act on. **Monthly reset.** Quotas are platform-set and
platform-customisable per Principal and per Tenant (not self-service);
`tenant_admin` and `responder` **request increases from the UI**,
creating an idempotency-keyed service-desk ticket pre-filled with
`graft_tenant_id`, current ceiling, observed consumption and the
triggering `graft_run_id`, applied by a `platform_admin` as an audited
policy version bump (fallback: a deep link carrying the same context).
**In-product quota indicator** per Principal and per Tenant, **threshold
notification** (proposed 80%) via ADR-0035's path, and **platform
monitoring** of consumption vs ceiling, at-cap rejection rate, and
quota-request rate and time-to-fulfil.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Uniform at-cap behaviour across all scopes (e.g. always hard-stop, or always graceful-terminate) | ❌ Rejected | Wrong for at least one scope either way: hard-stopping a per-run cap wastes the investigation already done, while graceful-terminating a per-tenant monthly cap would let new runs keep starting past the limit. |
| Degrade to a cheaper model when a budget cap is approached | ❌ Rejected | Model selection is a platform decision driven by evals and availability; switching mid-run would silently change the quality characteristics an operator is about to act on. |
| Self-service quota increases | ❌ Rejected | Quotas are platform-set and platform-customisable, not self-service; increases go through an idempotency-keyed service-desk ticket applied by a `platform_admin` as an audited policy version bump. |
| Per-scope at-cap behaviour (graceful terminate for per-run; hard stop for per-principal/per-tenant; throttle/queue for per-connection) | ✅ Chosen | Matches what each scope is actually protecting: a run's own progress, a Tenant's/Principal's monthly usage, or customer infrastructure capacity. |

## 4. Consequences

- **Positive —** a per-run cap never produces a bare failure — it emits
  the best hypothesis formed so far; a per-connection throttle never
  fails the run outright either, protecting customer infrastructure
  without collateral damage to the investigation.
- **Negative / accepted trade —** per-tenant and per-principal caps are a
  hard stop — new runs are rejected outright once the monthly ceiling is
  hit, with no degrade-to-cheaper-model relief valve.
- **Follow-on work —** quota-increase requests flow through an
  idempotency-keyed service-desk ticket pre-filled with context
  (`graft_tenant_id`, current ceiling, observed consumption, triggering
  `graft_run_id`); in-product indicators and an 80% threshold
  notification (via ADR-0035) are required.
- **Revisit trigger —** none observed; consumption vs. ceiling, at-cap
  rejection rate, and quota-request rate/time-to-fulfil are tracked as
  ongoing platform metrics.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).
