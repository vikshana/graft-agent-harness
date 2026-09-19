# Gate 0.3 evidence

This directory is reserved for redacted experiment output. The runner writes
`result.json` and `commands.json` only after the local containers are started.
The bounded Test 2 and Test 3 lane writes `test-2-result.json`,
`test-2-commands.json`, `test-3-result.json`, and `test-3-commands.json`.
Every command output is redacted before it is written. No credentials are
stored here. Gate 0 fast CI must not select the `gate_0_3` marker; these
experiments are explicit integration evidence.

Evidence interpretation is deliberately conservative. Test 2 is
`REDUCED_FIDELITY`/`INCOMPLETE`: the historical run used DBOS private recovery
internals and a synthetic orphan detector, so it does not prove a supported
cross-executor recovery contract. The current lane does not call those
internals. Test 3 is also `REDUCED_FIDELITY`; its helper-only unchanged hash is
labelled false-compatible, not compatible. `recovery-race.json` is the
decisive supported-API post-effect race probe, not a DBOS recovery Test 1, 4 or
5 pass claim.

The probe observed at-least-once external execution: one Run/step-derived key
produced two raw calls, the keyed receiver applied one effect, and DBOS
converged the checkpoint and Run outcome. This is not an external execution
fence. Confirmed termination and leases are availability and duplicate-exposure
controls, not the semantic proof. ADR-0076 remains proposed and this evidence
does not accept it.

The current supported-API barrier run is retained in `recovery-race.json`. Its
three SIGSTOP cases and executor-specific system-database partition completed
with public status `SUCCESS`, run-unique executor IDs, and the winning executor
equal to scenario B. Receiver counts were before effect (`2` raw / `1` keyed),
post-effect before checkpoint (`2` / `1`), and after the last step before
outcome (`1` / `1`). Each case ran two concurrent `DBOSClient.resume_workflow`
attempts and killed a reaper after public resume acceptance while its status was
`ENQUEUED`, then retried it to terminal success. The synthetic receiver
asserted that every raw call used `graft_run_id:durable_step_id`; this is a
test-service contract assertion, not real Grafana, Kubernetes or provider
support. The run used only public DBOS APIs and did not read or mutate DBOS
system tables.

The reservation is a durable application-DB CAS keyed by
`(graft_run_id, application_revision)` with an owner generation and explicit
`AVAILABLE`, `RESERVED`, `RECOVERY_REQUIRED` and `TERMINAL` states. A reaper
crash leaves `RESERVED`; retry can select only an explicit recovery-state row
through a generation CAS, not an elapsed lease. Exactly one selected reaper
invokes public `DBOSClient.resume_workflow`; rejected contenders emit
`reaper_not_selected` and do not invoke DBOS. Wrong-revision selection is
rejected before DBOS. This proves application reaper selection, not arbitrary
direct DBOSClient caller fencing; production bypass prevention is the
ADR-0048 runtime import boundary.

The matrix records `PASS` only after asserting fault-command return code zero,
the reconnect command return code zero, original A handle outcome/error, B or
reaper terminal outcome, explicit revision-scoped application CAS lease,
container elapsed effort, and the final B executor ID. A matrix failure remains
`FAILED`/`INCOMPLETE` and is not converted to reduced fidelity.

The Phase 1 effect inventory and classifications are retained in
`phase-1-effect-inventory.json`. Every currently unimplemented or unverified
effect is classified `B` with operator escalation. Each has a distinct
`promotion_criteria` field describing what must be proven before it may become
candidate `A`; the inventory makes no claim of real external-system support.

The ADR-0077 comparison lane directly established that changing DBOS 2.31.1 to
3.0.0 changes the automatic application version for the same registered
workflow source and application name. The DBOS 2.31.1 system schema recorded
migration 108; the DBOS 3.0.0 system schema recorded migration 114. These were
separate disposable launches, not a cross-version recovery or operational
drain test. A DBOS 3.0.0 helper-only change also changed runtime output while
the automatic version remained
`6291bf83d0ad38ca22f83e659454e749`: an observed false-compatible result.

ADR-0077 is accepted and supersedes ADR-0046: every
mutually versioned release receives an explicit released application
compatibility revision, not a mutable Git SHA or image tag, and every prior
release cohort drains. Old-version capacity must remain until `PENDING`,
`ENQUEUED`, and `DELAYED` work is empty; orphaned cohorts alert; recovery stays
within a matching revision; and rollback is a reverse drain. The comparison
lane did not test those operational controls. This lane does not alter ADR-0077
acceptance and records its remaining operational evidence separately.

The subsequent Test 2 report retains the exact blocker: explicit revisions and
all three active states were seeded, orphan observations and reverse drain were
recorded, but the public DBOS resume API cannot safely enforce expected
executor/application-revision selection. It therefore remains reduced fidelity
and does not claim accepted ADR-0077 operational evidence.

The CI job intentionally fails on this `REDUCED_FIDELITY` Test 2 result. The
local evidence therefore records the exact remaining blocker rather than
claiming a Gate 0.3 pass.

Test 3 is `PASS_WITH_ADR_0077_MITIGATION` for version-policy purposes: its
reduced-fidelity helper/dependency observations are retained, but accepted
ADR-0077 supplies the explicit released compatibility-revision and drain
mitigation. The report is not treated as proof of the automatic hash policy.

Gate 0.3 remains not closed; the bounded lane does not change Gate 0.3 or
ADR-0076 status. The current evidence is:

| Required test | Status |
|---|---|
| Recovery barrier/partition matrix, including before-effect, post-effect/pre-checkpoint, post-final-step/pre-outcome, and system-database network-cut cases | `PASS` in the bounded container matrix; redacted result retained |
| Both-handle outcomes and concurrent resume/crash cases | `PASS` for the public handles/results observed, concurrent resumes, and reaper crash/retry |
| Phase 1 external-effect inventory with receiving-boundary idempotency tests, or an explicit operator-escalation classification where durable idempotency is unavailable | Inventory complete; all currently unimplemented/unverified effects remain `B`/operator escalation with explicit `promotion_criteria` |
