---
id: ADR-0044
title: Budget enforcement is split across three layers
status: accepted
date: 2026-09-12
deciders: []
category: tenancy
tags: [tenancy, scoping, rbac]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/tenancy-and-scoping.md
legacy_id: D44
---

# ADR-0044 — Budget enforcement is split across three layers

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D44`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).

---

## 1. Context

ADR-0017's ceiling chain establishes *what* the limits are, but not
*where* each is enforced. Concurrency, graph-depth/loop protection, and
customer-infrastructure protection are three genuinely different concerns
that could be enforced in one place or split across the components that
actually have the relevant information — and a decision was needed on
whether combining them into one enforcement point was worth the coupling.

## 2. Decision

**Budget/circuit-breaker enforcement is deliberately split across three
layers, not accidentally duplicated.** Orchestrator: concurrent runs per
workspace via **durable-queue partition keys** (partitioned queues apply
concurrency and rate limits **per partition** — a native implementation of
**ADR-0017**'s ceiling chain), plus per-run wall-clock via deadlines.
Agent: max graph depth (~15), loop breakers (same tool + same args
twice), per-run token/cost caps reported via ADR-0029's
`budget_consumed`/`budget_warning`. Tool Gateway: per-connection
throttles protecting *customer* infrastructure, keyed by connection and
independent of workspace quota.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| One centralised enforcement point for all budget/circuit-breaker concerns | ❌ Rejected | Would couple concerns (queue concurrency, graph-depth/loop protection, customer-infrastructure protection) that are naturally owned by different components with different information available to them. |
| Split enforcement across three layers — orchestrator (queue partitioning, wall-clock), agent (graph depth, loop breakers, token/cost caps), Tool Gateway (per-connection throttles) | ✅ Chosen | Each layer enforces the concern it has the information and natural leverage to enforce; deliberate split, not accidental duplication. |

## 4. Consequences

- **Positive —** each enforcement mechanism lives at the layer that
  naturally has the information to enforce it (e.g. the Tool Gateway
  protects customer infrastructure per connection, independent of
  workspace quota).
- **Negative / accepted trade —** three separate enforcement points must
  each be kept correct and consistent with ADR-0017's ceiling chain,
  rather than one place to audit.
- **Follow-on work —** per-run token/cost caps are reported via ADR-0029's
  `budget_consumed`/`budget_warning` events, tying this decision into the
  streaming event model.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).
