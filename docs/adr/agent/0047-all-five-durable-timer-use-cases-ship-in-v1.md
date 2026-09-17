---
id: ADR-0047
title: All five durable-timer use cases ship in v1
status: accepted
date: 2026-09-12
deciders: [ ]
category: agent
tags: [ agent, orchestration, durability ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ADR-0035 ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/durable-execution.md
legacy_id: D47
---

# ADR-0047 — All five durable-timer use cases ship in v1

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D47`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

The durability-engine briefing argued that pervasive timer use "shifts strongly toward Temporal." Five candidate
durable-timer use cases needed a v1-scope decision, and ADR-0035's unbounded HITL approval wait needed reconciling with
ADR-0046's version pinning — an unanswered approval would otherwise pin a deploy colour alive indefinitely.

## 2. Decision

**All five durable-timer use cases are in v1**: HITL approval waits (`recv`
timeout), **scheduled/recurring RCA** (`create_schedule`, per workspace), **infra-memory refresh `*/15`**
(`apply_schedules`), **auto-close of stale runs**, and **per-run wall-clock deadline** (`deadline_epoch_ms`). Timers
proving pervasive does **not** reopen ADR-0037 — the briefing argued pervasive timers "shift strongly toward Temporal",
but DBOS covers all five natively (durable sleep, `recv` timeouts, database-stored cron schedules that are
creatable/pausable/deletable at runtime, each firing on exactly one worker). **Consequence — HITL approval waits are now
bounded, refining ADR-0035:** an unanswered approval **expires** (closing the run as
`expired`) rather than waiting indefinitely, because an unbounded wait combined with ADR-0046's version pinning would
pin a deploy colour alive for weeks. This preserves ADR-0035's deliberate "no escalation path" stance while making the
drain window finite. Expiry duration is an untaken product decision, must exceed a realistic weekend on-call handover
(≥72h), and is the effective upper bound on colour retention. **Scheduled RCA runs are
`system_initiated` and therefore structurally read-only per ADR-0013.**

## 3. Considered options

| Option                                                                                     | Verdict               | Why                                                                                                                                   |
|--------------------------------------------------------------------------------------------|-----------------------|---------------------------------------------------------------------------------------------------------------------------------------|
| Treat pervasive timer use as a reason to reopen ADR-0037 (durable-execution engine choice) | ❌ Rejected           | DBOS covers all five timer use cases natively — no need to revisit the engine choice.                                                 |
| Ship all five durable-timer use cases in v1                                                | ✅ Chosen             | All five are natively supported by DBOS; no reason to defer any of them.                                                              |
| Leave HITL approval waits unbounded, per ADR-0035's original "no escalation path" stance   | ❌ Rejected (refined) | An unbounded wait combined with ADR-0046's version pinning would pin a deploy colour alive for weeks; approval waits must now expire. |

## 4. Consequences

- **Positive —** all five timer use cases ship without reopening the durable-execution engine decision.
- **Negative / accepted trade —** HITL approval waits are now bounded — an unanswered approval expires (closing the run
  as `expired`) rather than waiting indefinitely.
- **Follow-on work —** scheduled RCA runs are `system_initiated` and therefore structurally read-only per ADR-0013.
- **Revisit trigger —** expiry duration remains an untaken product decision; it must exceed a realistic weekend on-call
  handover (≥72h).

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/durable-execution.md`](../../design/durable-execution.md).
