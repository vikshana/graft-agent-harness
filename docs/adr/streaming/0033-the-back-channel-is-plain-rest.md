---
id: ADR-0033
title: The back-channel is plain REST
status: accepted
date: 2026-09-12
deciders: []
category: streaming
tags: [streaming, events]
supersedes: []
superseded_by: []
amends: []
amended_by: [ADR-0045]
relates_to: []
design: ../../design/streaming-and-events.md
legacy_id: D33
---

# ADR-0033 — The back-channel is plain REST

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D33`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Back-channel (cancel/signal/approve/request-control/release-control) is plain REST**, idempotency-keyed to the run, identical across web, Grafana, and Slack — **locks R7** (superseding its "recommendation" status). Non-driver callers are rejected per ADR-0032's soft-lock, or redirected to `request-control`. **Signal delivery is a Postgres signal table + `LISTEN/NOTIFY`**, reusing ADR-0030's substrate — **superseded by ADR-0045 (2026-09-12)**: DBOS `send`/`recv` replaces the bespoke signal table now that the orchestrator is chosen. The REST back-channel itself is unchanged, and ADR-0030's event log is unaffected. **Cancel/signal is checked at every tool-call boundary** (not only at coarse checkpoints) — a concrete requirement carried into the durable-execution design: the execution loop needs a signal-check hook between every tool call, bounding cancel latency to the current tool call's duration.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
