---
id: ADR-0078
title: Phase 1 disables automatic cross-executor recovery
status: proposed
date: 2026-09-19
deciders: [project owner]
category: agent
tags: [agent, dbos, recovery, executor-identity, phase-1]
supersedes: []
superseded_by: []
amends: [ADR-0076]
amended_by: []
relates_to: [ADR-0038, ADR-0037, ADR-0077]
design: ../../design/durable-execution.md
verified: 2026-09-19
phase: Phase 1
---

# ADR-0078 — Phase 1 disables automatic cross-executor recovery

> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism:
> [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

ADR-0038 already makes work rediscovery `executor_id`-pinned: a Run is
recoverable only when the same executor identity returns, with the matching
application version. Proposed ADR-0076 describes at-least-once execution and
durable receiving-boundary idempotency, but its current wording can be read as
permitting automatic takeover by a different executor.

Gate 0.3 did not establish a supported-API ownership and revision fence for
that takeover. Its historical private-recovery lane is explicitly reduced
fidelity, and the supported-API evidence records the inability to safely
condition resume on an expected executor and application revision. The
[Gate 0.3 evidence](../../../specs/phase-1-walking-skeleton/evidence/gate-0.3/README.md)
and its [supported-API recovery probe](../../../specs/phase-1-walking-skeleton/evidence/gate-0.3/recovery-race.json)
remain historical evidence; they do not prove a cross-executor recovery
contract or close the gate.

The [Temporal comparison spike](../../../specs/phase-1-walking-skeleton/evidence/temporal-spike/README.md)
also observed at-least-once activity execution and relied on the synthetic
receiver's durable key rather than an engine-level external-effect fence. It
is comparison evidence, not an engine-selection decision.

## 2. Decision

**Pending formal owner acceptance, Phase 1 shall not perform or claim automatic
cross-executor recovery.** Automatic restart recovery is limited to a matching
executor identity and the explicit released application compatibility revision
recorded for the Run. When the identity or revision cannot be established, an
executor is alive-but-silent, or a Run is ambiguous or stuck, the system must
record the recovery state, must not resume it on another executor, and must
escalate it to an operator. This narrows the Phase 1 application of proposed
ADR-0076 and does not amend the accepted executor-pinned boundary in ADR-0038.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Allow only matching executor identity and explicit application revision restart recovery, with operator escalation for ambiguity | ✅ Owner-selected proposal | It preserves the executor-pinned boundary already recorded in ADR-0038 and avoids claiming an ownership/revision fence that Gate 0.3 did not prove. |
| Adopt DBOS Conductor for cross-executor recovery | ❌ Not selected | It would change the product, deployment and commercial boundary excluded by ADR-0037; no Conductor selection is made by this proposal. |
| Adopt Temporal for cross-executor recovery | ❌ Not selected | The Temporal spike still observed at-least-once activity execution and did not provide an external-effect fence; selecting it would require a separate engine decision and migration assessment. |
| Renew the custom DBOS cross-executor recovery timebox | ❌ Not selected for Phase 1 | The supported-API ownership and revision blocker remains unresolved. Reopening the timebox requires a new proposal and fresh evidence rather than an implicit Phase 1 waiver. |

## 4. Consequences

- **Positive —** Phase 1 has a conservative, testable recovery boundary: a
  matching executor identity and released compatibility revision are required
  before automatic restart recovery, and uncertain ownership cannot silently
  become duplicate execution.
- **Negative / accepted trade —** Phase 1 no longer claims recovery after a
  worker loss unless the same executor identity returns. A different healthy
  executor does not automatically take over; an ambiguous or stuck Run waits
  for operator action, reducing availability in exchange for not asserting an
  unproven ownership fence.
- **At-least-once consequence —** matching-identity restart recovery may still
  repeat a DBOS step. The receiving-boundary idempotency and operator-escalation
  requirements in proposed ADR-0076 remain applicable within that narrower
  boundary.
- **Follow-on work —** implement explicit executor-identity and released
  compatibility-revision checks, typed ambiguous/stuck recovery states, and an
  operator runbook. Retain the raw Gate 0.3 and Temporal evidence unchanged;
  this proposal does not claim Gate 0.3 or Phase 1 completion.
- **Exact revisit trigger —** reopen this boundary only through a new ADR when
  a repeatable supported-API test on the pinned Phase 1 dependencies proves an
  enforceable executor-identity and released-revision fence across alive-but-
  silent, system-database partition, concurrent-resume and reaper-crash cases,
  with effect-inventory and operator-escalation evidence; or when the owner
  explicitly starts a separately documented Conductor, Temporal or renewed
  custom-DBOS evaluation. Until that trigger is met, cross-executor automatic
  recovery remains disabled and no failed experiment is a waiver.

## 5. Verification

On 2026-09-19, the retained Gate 0.3 evidence showed that the supported DBOS
API could not safely condition resume on an expected executor and application
revision; the historical private-recovery result was classified
`REDUCED_FIDELITY`/`INCOMPLETE`. The retained Temporal spike on the same date
showed duplicate raw activity delivery after worker loss, with the synthetic
receiver—not Temporal—collapsing the logical effect. These sources support
the proposed scope boundary and the accepted availability trade, but do not
verify implementation or formal owner acceptance.

Before this ADR can be accepted, the verification record must include:

1. a same-executor identity and explicit released-revision restart test;
2. negative tests showing that a different executor or revision cannot resume
   automatically; and
3. an ambiguous/alive-but-silent/stuck Run test showing durable state,
   operator escalation, and no automatic cross-executor takeover.

The result must retain the exact dependency versions, commands, expected and
actual outcomes, and redacted artefacts under the Phase 1 evidence directory.
