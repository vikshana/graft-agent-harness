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

Limits (budgets, rate limits, concurrency) exist at multiple scopes —
platform, tenant, workspace, user, run — and a rule was needed for how
those scopes combine: does a more permissive limit at a lower scope
override a stricter one above it, or does the strictest scope always win?
Separately, some limits exist to protect *customer* infrastructure (e.g. a
shared Kubernetes control plane) rather than to meter our own usage, and
those two purposes needed distinguishing.

## 2. Decision

**Limits form a ceiling chain** —
`platform ≥ tenant ≥ workspace ≥ user ≥ run`, effective limit is the
minimum across scopes. Platform ceilings are **not customer-raisable**.
Per-connection throttles (protecting *customer* infrastructure, e.g. a
shared K8s control plane) are keyed by connection, independent of
workspace quota.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Allow a lower-scope limit to exceed a higher-scope one | ❌ Rejected | Would let a Tenant or user configuration silently override a platform-level ceiling, which must remain non-customer-raisable. |
| A strict ceiling chain (`platform ≥ tenant ≥ workspace ≥ user ≥ run`), effective limit = minimum across scopes | ✅ Chosen | Guarantees the platform ceiling always holds regardless of what any lower scope configures. |
| Fold per-connection throttles (protecting customer infrastructure) into the same chain as workspace/tenant usage quotas | ❌ Rejected | These protect two different things — customer infrastructure capacity vs. our own usage metering — and conflating them would tie a customer-infrastructure protection to a quota it has nothing to do with. |

## 4. Consequences

- **Positive —** a platform ceiling is guaranteed to hold no matter what
  any Tenant, workspace, user or run configures beneath it.
- **Negative / accepted trade —** per-connection throttles must be tracked
  and enforced independently of workspace/tenant quota, rather than being
  folded into one unified limit model.
- **Follow-on work —** amended by ADR-0057, which refines the chain
  (dropping the workspace layer per ADR-0051's scope collapse) and adds
  distinct at-cap behaviour per scope.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).
