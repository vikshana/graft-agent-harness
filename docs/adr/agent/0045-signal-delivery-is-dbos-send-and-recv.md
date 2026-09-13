---
id: ADR-0045
title: Signal delivery is DBOS send and recv
status: accepted
date: 2026-09-12
deciders: []
category: agent
tags: [agent, orchestration, durability]
supersedes: []
superseded_by: []
amends: [ADR-0033]
amended_by: []
relates_to: []
design: ../../design/durable-execution.md
legacy_id: D45
---

# ADR-0045 — Signal delivery is DBOS send and recv

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D45`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Signal delivery is DBOS `send`/`recv`, superseding ADR-0033's provisional Postgres signal table + `LISTEN/NOTIFY`.** `DBOS.send()` is persisted with exactly-once delivery from workflows and is callable from outside the worker via `DBOSClient` or from PL/pgSQL (`dbos.send_message`); `DBOS.recv(topic, timeout_seconds)` is the durable multi-hour HITL wait. **ADR-0033's REST back-channel is unchanged** — the handler now calls `send` instead of inserting a row. **ADR-0030's event log is entirely unaffected**, preserving `04` §7.7: streaming remains independent of the orchestrator choice, and we keep our own event log rather than DBOS's `set_event`/streaming features (ADR-0029/ADR-0030/ADR-0031 intact).

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
