---
id: ADR-0047
title: All five durable-timer use cases ship in v1
status: accepted
date: 2026-09-12
deciders: []
category: agent
tags: [agent, orchestration, durability]
supersedes: []
superseded_by: []
amends: [ADR-0035]
amended_by: []
relates_to: []
design: ../../design/durable-execution.md
legacy_id: D47
---

# ADR-0047 — All five durable-timer use cases ship in v1

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D47`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**All five durable-timer use cases are in v1**: HITL approval waits (`recv` timeout), **scheduled/recurring RCA** (`create_schedule`, per workspace), **infra-memory refresh `*/15`** (`apply_schedules`), **auto-close of stale runs**, and **per-run wall-clock deadline** (`deadline_epoch_ms`). Timers proving pervasive does **not** reopen ADR-0037 — the briefing argued pervasive timers "shift strongly toward Temporal", but DBOS covers all five natively (durable sleep, `recv` timeouts, database-stored cron schedules that are creatable/pausable/deletable at runtime, each firing on exactly one worker). **Consequence — HITL approval waits are now bounded, refining ADR-0035:** an unanswered approval **expires** (closing the run as `expired`) rather than waiting indefinitely, because an unbounded wait combined with ADR-0046's version pinning would pin a deploy colour alive for weeks. This preserves ADR-0035's deliberate "no escalation path" stance while making the drain window finite. Expiry duration is an untaken product decision, must exceed a realistic weekend on-call handover (≥72h), and is the effective upper bound on colour retention. **Scheduled RCA runs are `system_initiated` and therefore structurally read-only per ADR-0013.**

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
