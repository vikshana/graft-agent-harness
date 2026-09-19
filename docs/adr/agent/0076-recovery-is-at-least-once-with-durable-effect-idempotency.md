---
id: ADR-0076
title: Recovery is at least once with durable effect idempotency
status: proposed
date: 2026-09-19
deciders: [project owner]
category: agent
tags: [agent, dbos, recovery, idempotency, reaper]
supersedes: []
superseded_by: []
amends: [ADR-0038]
amended_by: []
relates_to: [ADR-0037, ADR-0043, ADR-0050, ADR-0060]
design: ../../design/durable-execution.md
verified: 2026-09-19
phase: Phase 1
---

# ADR-0076 — Recovery is at least once with durable effect idempotency

> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism:
> [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

ADR-0038 assigns work rediscovery to the system rather than DBOS Conductor, and
the Phase 1 implementation requires recovery of abandoned Runs. Gate 0.3
tested DBOS 3 against separate PostgreSQL application/system databases and
transaction-mode PgBouncer. Its public API did not provide a safe way to
distinguish an executor that is dead from one that is alive but silent.

The supported-API probe then observed a post-effect, pre-checkpoint duplicate:
the same Run/step made two raw calls, DBOS converged the checkpoint and outcome,
and a keyed receiver applied one effect. This demonstrates that DBOS recovery
can repeat external execution. DBOS state convergence is therefore not an
external execution fence.

The observed evidence is
[`evidence/gate-0.3/result.json`](../../../specs/phase-1-walking-skeleton/evidence/gate-0.3/result.json),
especially the `G03-B` classification, and the redacted command record is
[`evidence/gate-0.3/commands.json`](../../../specs/phase-1-walking-skeleton/evidence/gate-0.3/commands.json).
Both were verified on 2026-09-18.

## 2. Decision

DBOS recovery is at least once: duplicate step execution is permitted, and DBOS
converges the step checkpoint and Run outcome after the duplicate execution, but
DBOS does not fence external execution. Every external effect eligible for
automatic recovery must therefore be durably idempotent at its receiving
boundary, using a stable idempotency key derived from `graft_run_id` and the
durable step identity. An effect without that property is not automatically
recoverable and requires operator escalation. Confirmed termination and leases
are availability and duplicate-exposure controls, not the semantic proof of
effect safety.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| At-least-once DBOS recovery with durable receiving-boundary idempotency | ✅ Chosen | DBOS converges its checkpoint and Run outcome after duplicate execution; a stable `graft_run_id`/step-derived key makes a repeat safe at the receiving boundary. |
| Require confirmed executor termination before automatic recovery | ❌ Rejected as the semantic proof | It can improve availability and reduce duplicate exposure, but termination confirmation does not prove that an earlier external call did not already happen. It can also delay recovery during host or network partitions. |
| Use a lease or independent fence as the semantic proof | ❌ Rejected as the semantic proof | A lease can constrain future execution when its authority and failure behaviour are proven, but it does not undo an external effect that happened before the fence. It remains an operational control, not the effect-safety guarantee. |
| Automatically recover an effect with no durable receiving-boundary idempotency | ❌ Rejected | DBOS cannot make that effect exactly once. Such an effect requires operator escalation rather than automatic recovery. |
| Rely on a stale heartbeat or timeout as recovery proof | ❌ Rejected | It cannot distinguish a dead executor from an alive-but-silent executor and can expose duplicate execution. Gate 0.3 did not treat timeout as recovery proof. |

## 4. Consequences

- **Positive —** DBOS recovery can remain available while duplicate external execution is made safe at a durable receiving boundary.
- **Negative / accepted trade —** raw external calls may occur more than once, and every automatically recoverable effect needs a receiving boundary that durably honours the stable key. Effects that cannot meet that contract wait for an operator.
- **Operational control —** confirmed termination and leases may reduce duplicate exposure or improve availability, but neither is treated as the semantic proof. A stale heartbeat alone cannot authorise an effect that lacks the idempotency contract.
- **Follow-on work —** complete the recovery barrier/partition matrix, both-handle and concurrent-resume/crash cases, and the Phase 1 external-effect inventory with receiving-boundary idempotency tests. Keep this ADR proposed until that evidence and the remaining Gate 0.3 decisions are reviewed.
- **Revisit trigger —** reopen if DBOS provides a verified external-execution fence, or if the Phase 1 effect inventory identifies a receiving-boundary contract that changes the automatic-recovery boundary.

## 5. Verification

On 2026-09-19, the supported-API probe used DBOS 3.0.0 with local PostgreSQL
16 application and system databases and transaction-mode PgBouncer. Its
[`recovery-race.json`](../../../specs/phase-1-walking-skeleton/evidence/gate-0.3/recovery-race.json)
records two raw calls for one Run/step-derived key, one keyed effect, a
same-version replacement reaching `SUCCESS`, and the original execution
reporting duplicate execution before converging on the recorded result. This
verifies the observed at-least-once boundary and DBOS checkpoint/outcome
convergence in that scenario; it does not prove a general reaper, an executor
fence, or idempotency for a real receiving system.

The complete recovery matrix and Phase 1 external-effect inventory remain
outstanding. Gate 0.3 is not closed by this probe, and this ADR remains
proposed.
