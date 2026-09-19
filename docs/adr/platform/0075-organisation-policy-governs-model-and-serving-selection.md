---
id: ADR-0075
title: Organisation policy governs model and serving selection
status: accepted
date: 2026-09-17
deciders: []
category: platform
tags: [model, serving, policy, provisional]
supersedes: []
superseded_by: []
amends: [ADR-0049, ADR-0057]
amended_by: []
relates_to: [ADR-0008, ADR-0034, ADR-0041, ADR-0049, ADR-0057, ADR-0062]
design: ../../design/platform-topology.md
---

# ADR-0075 — Organisation policy governs model and serving selection

> **Status: accepted (2026-09-17).** This closes spike S4. The choice remains
> provisional until the Phase 2 model-routing session.
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism:
> [`../../design/platform-topology.md`](../../design/platform-topology.md).

---

## 1. Context

Phase 1 needs a model and serving arrangement, but the model-routing session is
scheduled for Phase 2. The two independent regional deployments and their data
residency boundary mean that a project-level provider or model assumption could
be unavailable or non-compliant in a home region. Model selection must also
remain compatible with token streaming, per-call instrumentation, prompt-layer
caching, and the budget rule that forbids changing quality characteristics
mid-Run.

## 2. Decision

**Phase 1 will use whichever model and serving arrangement the organisation's
policy designates for the Run's home region.** The policy must select an approved
arrangement that satisfies the applicable residency and compliance constraints
and the existing streaming, instrumentation, context, and budget decisions;
the selected model is fixed for the Run, with no mid-Run fallback or degrade-to-
a-cheaper-model behaviour.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Use the model and serving arrangement dictated by organisation policy | ✅ Chosen | Keeps provider approval, regional availability, residency, and compliance under the organisation's governing control without hard-coding a Phase 2 routing outcome into Phase 1. |
| Select one named commercial or self-hosted model for both regions | ❌ Rejected | It would turn a provisional spike into an unverified provider commitment and could conflict with organisation policy or regional availability. |
| Select different project-owned models per region | ❌ Rejected | It would duplicate policy ownership in the harness and require regional model evals before the Phase 2 routing decision. |
| Add a fallback chain or degrade to a cheaper model at a budget cap | ❌ Rejected | ADR-0057 prohibits changing the quality characteristics of an in-flight Run. |

## 4. Consequences

- **Positive —** Phase 1 can proceed without baking a provider, model, or
  serving topology into the harness; organisation policy remains the authority
  for approved regional choices.
- **Negative / accepted trade —** model quality, cost, and availability are
  policy inputs rather than a single project-wide constant; evals and quota
  numbers must be recorded for each policy-selected arrangement.
- **Follow-on work —** the policy owner must publish the approved arrangement
  for each home region before deployment, and the Phase 2 routing session must
  revisit this decision rather than treating the Phase 1 arrangement as
  permanent.
- **Revisit trigger —** the Phase 2 model-routing session, or an organisation
  policy change that alters the approved model or serving arrangement.

## 5. Verification

Verified 2026-09-17 against the S4 spike brief and the accepted constraints in
ADR-0049 and ADR-0057. No live provider or model comparison was performed;
that work is intentionally deferred to the Phase 2 model-routing session.
