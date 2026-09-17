---
id: ADR-0005
title: Observability is OTel-native
status: accepted
date: 2026-09-12
deciders: [ ]
category: observability
tags: [ observability, audit, compliance ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/audit-and-attribution.md
legacy_id: D5
---

# ADR-0005 — Observability is OTel-native

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D5`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/audit-and-attribution.md`](../../design/audit-and-attribution.md).

---

## 1. Context

v1 needs a telemetry pipeline for traces, metrics and logs that can fan out to multiple destinations (operational
dashboards, an eval sink, future vendor backends) without coupling every emitting service to a specific vendor's SDK or
wire format.

## 2. Decision

Observability is **OTel-native**. OTLP to a self-owned Collector; the Collector fans out.

## 3. Considered options

| Option                                                           | Verdict     | Why                                                                                                                                               |
|------------------------------------------------------------------|-------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| Vendor-specific SDK/wire format per backend                      | ❌ Rejected | The migrated register entry did not record a rejection rationale beyond the decision itself; couples every emitter to a specific vendor's format. |
| OTLP to a self-owned Collector, which fans out to multiple sinks | ✅ Chosen   | Decouples emitters from any single backend; the Collector is the one place that knows about destinations.                                         |

## 4. Consequences

- **Positive —** emitters (worker, tool gateway, etc.) only ever speak OTLP; adding or swapping a sink is a
  Collector-config change, not a code change across every service.
- **Negative / accepted trade —** the Collector becomes a piece of self-owned infrastructure that must be operated and
  kept healthy.
- **Follow-on work —** instrumentation content (what spans/metrics look like) is decided separately in ADR-0008; sink
  fan-out (operational vs. eval) is decided separately in ADR-0071.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/audit-and-attribution.md`](../../design/audit-and-attribution.md).
