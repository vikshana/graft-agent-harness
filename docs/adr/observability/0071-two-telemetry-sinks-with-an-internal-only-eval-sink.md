---
id: ADR-0071
title: Two telemetry sinks with an internal-only eval sink
status: accepted
date: 2026-09-12
deciders: [ ]
category: observability
tags: [ observability, audit, compliance ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ADR-0008 ]
amended_by: [ ]
relates_to: [ ADR-0040 ]
design: ../../design/audit-and-attribution.md
legacy_id: null
---

# ADR-0071 — Two telemetry sinks with an internal-only eval sink

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D71`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/audit-and-attribution.md`](../../design/audit-and-attribution.md).

---

## 1. Context

ADR-0008's multi-sink OTLP pipeline serves operational observability, but the eval pipeline (comparing prompt versions
against historical trajectories, ADR-0040's `fork_workflow`) needs telemetry with a different audience and a different
risk profile — it can carry richer trajectory detail than should ever be exposed to a customer-facing product feature.

## 2. Decision

**Two sinks, two jobs:** operational observability (traces/metrics/logs)
and an **internal-only** trajectory/eval sink. **No product feature may read from the eval sink's API.**

## 3. Considered options

| Option                                                                            | Verdict     | Why                                                                                                                                                              |
|-----------------------------------------------------------------------------------|-------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| One shared sink for both operational observability and eval/trajectory data       | ❌ Rejected | The migrated register entry did not record a rejection rationale beyond the decision itself; conflates two different audiences and risk profiles behind one API. |
| Two sinks: an operational sink and a separate, internal-only eval/trajectory sink | ✅ Chosen   | Lets the eval sink carry richer trajectory detail without that detail ever being exposed through a customer-facing product feature.                              |

## 4. Consequences

- **Positive —** the eval sink can carry richer trajectory data than would be safe to expose through any customer-facing
  surface.
- **Negative / accepted trade —** two sinks must be operated and kept populated consistently, rather than one.
- **Follow-on work —** the eval sink pairs with ADR-0040's
  `fork_workflow`/`list_workflow_steps()` to give a queryable trajectory source for comparing prompt versions against
  historical incidents.
- **Revisit trigger —** none observed; the hard rule ("no product feature may read from the eval sink's API") is the
  enforcement mechanism, not a policy that needs monitoring.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/audit-and-attribution.md`](../../design/audit-and-attribution.md).
