# Phase 1 evidence index

> **Evidence date:** 2026-09-19
>
> This index retains research inputs for the Phase 1 recovery-boundary
> decision. It is not a `research/` directory and does not duplicate the
> underlying reports.

## Accepted boundary

[ADR-0078](../../../docs/adr/agent/0078-phase-1-disables-automatic-cross-executor-recovery.md)
was formally accepted by the project owner on 2026-09-19. The accepted Phase 1
boundary is:

- automatic restart recovery requires a returning matching executor identity
  and the explicit released application compatibility revision recorded for the
  Run;
- a different executor must not take over a Run automatically;
- an alive-but-silent, ambiguous, or stuck Run is durably recorded and escalated
  to an operator; and
- at-least-once retries remain possible within the permitted matching-identity
  boundary, so an automatically recoverable external effect still requires
  receiving-boundary idempotency. An effect without that property requires
  operator escalation.

Acceptance fixes this Phase 1 scope boundary. It does not claim implementation,
Gate 0.3 completion, or Phase 1 completion. The unresolved custom DBOS Test 2
is not required to establish this accepted boundary. It remains
reduced-fidelity research and is not a foundation for future cross-executor
recovery.

## Retained research

| Research lane | What was completed | What remains deferred or unproven | Retained evidence |
|---|---|---|---|
| DBOS Gate 0.3 matrix and partial reaper discovery | A supported-API barrier/partition matrix observed at-least-once execution, public status/result convergence, concurrent resume attempts, reaper crash/retry handling, executor-specific system-database partition injection, and an application-owned CAS reaper reservation. | This is a bounded application/recovery-lane observation, not a DBOS executor fence or exactly-once external-effect result. The custom Test 2 remains `REDUCED_FIDELITY`/`INCOMPLETE`: public DBOS APIs could not safely condition resume on expected executor and released revision. It is deferred research, not a required Gate 0.3 acceptance condition after ADR-0078, and not a foundation for future cross-executor recovery. | [`gate-0.3/README.md`](gate-0.3/README.md), [`gate-0.3/recovery-race.json`](gate-0.3/recovery-race.json), [`gate-0.3/test-2-result.json`](gate-0.3/test-2-result.json), [`gate-0.3/phase-1-effect-inventory.json`](gate-0.3/phase-1-effect-inventory.json) |
| Conductor commercial and capability research | Public DBOS pricing and self-hosting documentation were recorded, together with documented recovery, version, configuration, licensing, and operational capabilities. The record explicitly does not claim that Conductor fences external effects. | A written vendor quote, production entitlement, licence metric, support terms, and answers to the retained commercial and recovery checklist remain outstanding. No Conductor selection, purchase, trial, key, deployment, or production claim was made. | [`conductor-evaluation/2026-09-19-conductor-commercial-capability-evidence.md`](conductor-evaluation/2026-09-19-conductor-commercial-capability-evidence.md) |
| Temporal comparison spike | The disposable synthetic lane classified as `PASS_WITH_LIMITATIONS`: worker death/retry and heartbeat timeout behaviour were observed; a post-effect worker death produced two raw deliveries and one keyed synthetic logical effect; the compatibility marker replayed successfully. | Temporal did not provide an engine-level external-effect fence. The synthetic receiver, not Temporal, collapsed the duplicate effect. The spike did not assess DBOS trajectories, DBOS queues, DBOS system-database/pooler topology, DBOS executor/reaper policy, or released compatibility-revision policy; no engine switch was selected. | [`temporal-spike/README.md`](temporal-spike/README.md), [`temporal-spike/result.json`](temporal-spike/result.json), [`temporal-spike/commands.json`](temporal-spike/commands.json) |

The raw artefacts, exact commands, dependency versions, redacted outputs, and
limitations remain in their existing evidence directories. This index records
their decision relevance without rewriting or copying those reports.

## Revisit rule

Reconsidering automatic cross-executor recovery requires a **new proposed ADR**;
ADR-0078 must not be edited to widen the boundary and no retained experiment is
an implicit waiver. A future proposal must state its alternatives and provide
supported-API, version-pinned evidence for alive-but-silent and partition cases,
concurrent resume, reaper failure, explicit executor and released-revision
selection, receiving-boundary effect safety, and operator escalation. A
Conductor proposal must first resolve the outstanding vendor quote and
entitlement questions. A Temporal proposal must include a separate engine and
migration decision. Until a new ADR is accepted, Phase 1 remains
no-automatic-cross-executor-recovery.
