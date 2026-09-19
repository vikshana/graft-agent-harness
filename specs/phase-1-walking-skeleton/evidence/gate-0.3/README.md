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
controls, not the semantic proof. Proposed ADR-0076 records the owner-selected
model and remains proposed.

The ADR-0077 comparison lane directly established that changing DBOS 2.31.1 to
3.0.0 changes the automatic application version for the same registered
workflow source and application name. The DBOS 2.31.1 system schema recorded
migration 108; the DBOS 3.0.0 system schema recorded migration 114. These were
separate disposable launches, not a cross-version recovery or operational
drain test. A DBOS 3.0.0 helper-only change also changed runtime output while
the automatic version remained
`6291bf83d0ad38ca22f83e659454e749`: an observed false-compatible result.

The owner-selected proposal in ADR-0077 is to supersede ADR-0046: every
mutually versioned release receives an explicit released application
compatibility revision, not a mutable Git SHA or image tag, and every prior
release cohort drains. Old-version capacity must remain until `PENDING`,
`ENQUEUED`, and `DELAYED` work is empty; orphaned cohorts alert; recovery stays
within a matching revision; and rollback is a reverse drain. The comparison
lane did not test those operational controls. ADR-0077 remains proposed and
still requires formal owner acceptance.

Gate 0.3 is not closed. Required evidence still outstanding:

| Required test | Status |
|---|---|
| Recovery barrier/partition matrix, including before-effect, post-effect/pre-checkpoint, post-final-step/pre-outcome, and system-database network-cut cases | Outstanding |
| Both-handle outcomes and concurrent resume/crash cases | Outstanding |
| Phase 1 external-effect inventory with receiving-boundary idempotency tests, or an explicit operator-escalation classification where durable idempotency is unavailable | Outstanding |
