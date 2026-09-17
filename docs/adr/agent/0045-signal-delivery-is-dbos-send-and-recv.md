---
id: ADR-0045
title: Signal delivery is DBOS send and recv
status: accepted
date: 2026-09-12
deciders: [ ]
category: agent
tags: [ agent, orchestration, durability ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ADR-0033 ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/durable-execution.md
legacy_id: D45
---

# ADR-0045 — Signal delivery is DBOS send and recv

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D45`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

ADR-0033 established a provisional Postgres signal table plus
`LISTEN`/`NOTIFY` for the back-channel, before the durable-execution engine (ADR-0037) was chosen. DBOS now provides its
own persisted, exactly-once
`send`/`recv` primitive, which needs reconciling with ADR-0033's provisional mechanism and with ADR-0030's independent
event log.

## 2. Decision

**Signal delivery is DBOS `send`/`recv`, superseding ADR-0033's provisional Postgres signal table + `LISTEN/NOTIFY`.**
`DBOS.send()` is persisted with exactly-once delivery from workflows and is callable from outside the worker via
`DBOSClient` or from PL/pgSQL (`dbos.send_message`);
`DBOS.recv(topic, timeout_seconds)` is the durable multi-hour HITL wait. **ADR-0033's REST back-channel is unchanged** —
the handler now calls `send`
instead of inserting a row. **ADR-0030's event log is entirely unaffected**, preserving `04` section 7.7: streaming
remains independent of the orchestrator choice, and we keep our own event log rather than DBOS's
`set_event`/streaming features (ADR-0029/ADR-0030/ADR-0031 intact).

## 3. Considered options

| Option                                                                                  | Verdict                  | Why                                                                                                                                                                |
|-----------------------------------------------------------------------------------------|--------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Keep ADR-0033's provisional Postgres signal table + `LISTEN/NOTIFY`                     | ❌ Rejected (superseded) | DBOS already provides a persisted, exactly-once `send`/`recv` primitive callable from the worker, `DBOSClient`, or PL/pgSQL — no need to maintain a bespoke table. |
| Adopt DBOS `send`/`recv` for signal delivery                                            | ✅ Chosen                | Persisted with exactly-once delivery; `recv(topic, timeout_seconds)` gives the durable multi-hour HITL wait natively.                                              |
| Move run events / streaming onto DBOS's own event log (`set_event`, streaming features) | ❌ Rejected              | ADR-0030's event log is unaffected — streaming stays independent of the orchestrator choice; we keep our own event log rather than DBOS's streaming features.      |

## 4. Consequences

- **Positive —** exactly-once signal delivery and durable multi-hour HITL waits, callable from outside the worker
  process.
- **Negative / accepted trade —** none recorded beyond superseding ADR-0033's provisional mechanism.
- **Follow-on work —** ADR-0033's REST back-channel is unchanged — the handler now calls `send` instead of inserting a
  row into the old signal table.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/durable-execution.md`](../../design/durable-execution.md).
