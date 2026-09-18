---
id: ADR-0076
title: Recovery requires confirmed termination or an independent fence
status: proposed
date: 2026-09-18
deciders: [project owner]
category: agent
tags: [agent, dbos, recovery, fencing, reaper]
supersedes: []
superseded_by: []
amends: [ADR-0038]
amended_by: []
relates_to: [ADR-0037, ADR-0043, ADR-0050, ADR-0060]
design: ../../design/durable-execution.md
verified: 2026-09-18
phase: Phase 1
---

# ADR-0076 — Recovery requires confirmed termination or an independent fence

> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism:
> [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

ADR-0038 assigns work rediscovery to the system rather than DBOS Conductor, and
the Phase 1 implementation requires a reaper that can recover abandoned Runs.
Gate 0.3 tested DBOS 3 against separate PostgreSQL application/system
databases and transaction-mode PgBouncer. Its public API did not provide a safe
way to distinguish an executor that is dead from one that is alive but silent.
Re-enqueueing while the original executor can still execute risks duplicate
steps and duplicate customer-side effects.

The observed evidence is
[`evidence/gate-0.3/result.json`](../../../specs/phase-1-walking-skeleton/evidence/gate-0.3/result.json),
especially the `G03-B` classification, and the redacted command record is
[`evidence/gate-0.3/commands.json`](../../../specs/phase-1-walking-skeleton/evidence/gate-0.3/commands.json).
Both were verified on 2026-09-18.

## 2. Decision

Propose that recovery may re-enqueue a Run only after confirmed termination of
the prior executor or after an independently proven fence/lease compare-and-set
that prevents the prior executor from executing further work; a stale heartbeat
alone must never justify re-enqueueing while the original executor may still
execute.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Re-enqueue after a stale heartbeat or timeout | ❌ Rejected | It cannot distinguish a dead executor from an alive-but-silent executor and can duplicate step execution. Gate 0.3 explicitly did not treat timeout as recovery proof. |
| Require confirmed executor termination before re-enqueue | ✅ Chosen conservative baseline | It avoids split-brain execution, although termination confirmation can delay recovery and may be difficult during host or network partitions. |
| Use an independently proven fence or lease compare-and-set | ✅ Permitted alternative | It can recover without waiting for process observation if the old executor is prevented from executing, but the fencing authority, atomicity and failure behaviour must be proven before use. |
| Rely on DBOS public `resume_workflow` semantics without an ownership fence | ❌ Rejected | The Gate 0.3 evidence did not establish that this API prevents an alive-but-silent executor from continuing. |

## 4. Consequences

- **Positive —** the recovery rule fails closed against the highest-risk duplicate-execution case.
- **Negative / accepted trade —** a confirmed-termination policy can leave work unavailable during ambiguous failures; a fence introduces another correctness-critical lease and authority path.
- **Follow-on work —** choose and prove one mechanism with crash, network-partition, delayed-heartbeat and concurrent-reaper tests before accepting this ADR or implementing production recovery.
- **Revisit trigger —** reopen if DBOS or the chosen fencing authority provides independently verified ownership semantics that change the safe recovery boundary.

## 5. Verification

On 2026-09-18, Gate 0.3 used DBOS 3.0.0 with local PostgreSQL 16 application
and system databases and transaction-mode PgBouncer. `G03-B` in
[`result.json`](../../../specs/phase-1-walking-skeleton/evidence/gate-0.3/result.json)
records `alive_but_silent_recovery` as unresolved and
`timeout_is_not_recovery_proof` as true. This is evidence for the conservative
disposition, not proof that either permitted production mechanism is complete.
