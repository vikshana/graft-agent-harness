---
id: ADR-0008
title: Instrumentation is OpenLIT plus hand-written spans over OTLP
status: accepted
date: 2026-09-12
deciders: [ ]
category: observability
tags: [ observability, audit, compliance ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ADR-0071 ]
relates_to: [ ]
design: ../../design/audit-and-attribution.md
legacy_id: D8
---

# ADR-0008 — Instrumentation is OpenLIT plus hand-written spans over OTLP

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D8`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/audit-and-attribution.md`](../../design/audit-and-attribution.md).

---

## 1. Context

Given OTel-native observability (ADR-0005), the content of the traces still needed deciding: LLM/tool-call
instrumentation is a well-trodden problem with existing auto-instrumentation libraries, but graph-node and
domain-specific semantics (run IDs, tenant scoping, tool authority) are not covered by any off-the-shelf library.

## 2. Decision

Instrumentation: **OpenLIT + hand-written spans** for graph nodes and domain semantics → **OTLP → Collector →
multi-sink**.

## 3. Considered options

| Option                                                                                                        | Verdict     | Why                                                                                                                                                                                           |
|---------------------------------------------------------------------------------------------------------------|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Hand-write all instrumentation, including LLM/tool-call spans                                                 | ❌ Rejected | The migrated register entry did not record a rejection rationale beyond the decision itself; duplicates what OpenLIT already provides for LLM/tool-call semantics.                            |
| OpenLIT auto-instrumentation for LLM/tool calls, plus hand-written spans for graph nodes and domain semantics | ✅ Chosen   | Covers the well-trodden LLM/tool-call surface with an existing library, while hand-writing only the domain-specific parts (graph nodes, run/tenant/authority context) that no library covers. |

## 4. Consequences

- **Positive —** LLM/tool-call spans come from a maintained library (OpenLIT) rather than being hand-maintained; only
  genuinely domain-specific spans are hand-written.
- **Negative / accepted trade —** two instrumentation sources (OpenLIT and hand-written) must be kept consistent in
  shape as they both flow through the same OTLP → Collector → multi-sink pipeline.
- **Follow-on work —** amended by ADR-0071, which splits the multi-sink fan-out into an operational sink and an
  internal-only eval sink.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/audit-and-attribution.md`](../../design/audit-and-attribution.md).
