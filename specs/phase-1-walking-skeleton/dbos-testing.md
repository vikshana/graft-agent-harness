# Handoff: DBOS recovery and versioning — test plan and go/no-go decision

**Audience:** an engineering agent with access to the Phase 1 repo, the Gate 0.3 harness, and the Gate 0.3 topology (DBOS 3.0.0, locked Python runtime, separate PostgreSQL application/system databases, transaction-mode PgBouncer).

**Your job:** run the tests in section 5, record evidence, apply the decision rules in section 6, and produce the deliverables in section 8. Do not change ADR status (Proposed → Accepted) until the blocking tests have results. The owner-selected recovery model is recorded in proposed ADR-0076; this brief does not accept that ADR or close Gate 0.3.

**Related ADRs:** ADR-0038 (work rediscovery owned by the system, not DBOS Conductor), ADR-0046 (DBOS auto-computed application version; no Git SHA or image tag pinning), and the two ADRs drafted from Gate 0.3 (reaper/recovery boundary; dependency-upgrade drains).

---

## 1. Decision required

Can Phase 1 proceed on open-source DBOS 3 **without Conductor**, with a self-built reaper and drain controller, while keeping duplicate customer-side effects acceptably controlled? Or must we (a) buy a Conductor license, (b) build our own fencing layer, or (c) spike Temporal?

## 2. Findings so far

Label key: **[doc]** = stated in vendor documentation, **[obs]** = observed in Gate 0.3, **[inf]** = inference, not verified.

### Recovery and detection

- **[doc]** DBOS without Conductor: assign each executor an executor ID. Each workflow is tagged with the ID of the executor that started it, and a restarting executor recovers only pending workflows with its own ID. Recovering another executor's workflows goes through the admin API's workflow-recovery endpoint, which takes a list of executor IDs. The endpoint is documented in older TypeScript-era pages; **confirm the supported programmatic entry point in DBOS 3.0.0 Python.**
- **[doc]** Conductor's detection is itself a timeout. An executor that disconnects is marked DISCONNECTED, then DEAD after a timeout (default 60 seconds), and only then are its workflows recovered. Conductor is not a fencing authority.
- **[doc]** DBOS states that recovery observations can be wrong (for example during rollouts), so a "zombie" executor can still be running a workflow. Its recovery model is at-least-once: steps can execute more than once, while workflow checkpoint and outcome state converges after concurrent execution. Concurrent execution is detected at step checkpoint and at terminal outcome write. The losing execution "parks" and receives the recorded outcome, and a conflict exception is raised that must not be ignored.
- **[doc]** The mechanism is a unique constraint on (workflow ID, step ID) in the checkpoint table.
- **[inf]** The conflict is detected only at checkpoint time, **after** the zombie has performed the step's external side effect. So external effects are protected only by step idempotency, not by DBOS.
- **[doc]** Temporal has the same property. Its server cannot tell a dead worker from a stalled one, and it reschedules on timeout. A timed-out activity that doesn't heartbeat can keep executing, and non-idempotent activities duplicate side effects. Neither engine removes the need for idempotent external effects, so this is not a reason to switch engines on its own.
- **[obs]** Gate 0.3: DBOS's public API gave no safe way to distinguish a dead executor from a live but silent one. This is consistent with the above and is not a DBOS-specific defect.

### Versioning

- **[doc]** DBOS recovers only workflows whose application version matches the current version. Default version is auto-computed from workflow source (documentation wording: hash of workflow source); it can be overridden by config. Blue-green upgrades are the recommended pattern.
- **[obs]** `G03-D`: recomputation is stable for identical source/runtime, and differs after source registration. **[inf, source-read only, not experimentally observed]** DBOS 3.0.0's hash also includes the DBOS package version and app name.
- **[doc]** DBOS Cloud keeps old-version machines alive until old-version PENDING/ENQUEUED work drains, and periodically recovers orphaned work onto a machine of the right version. Without Conductor or Cloud, **we must build this behavior ourselves.**
- **[doc, real-world report]** An in-place upgrade left runs of the previous version PENDING and never recovered because no old-version executor existed. Cancellation still worked because it is a status write. Source: https://github.com/czpython/druks/issues/619
- **[inf]** Risk asymmetry: a false drain (version changes needlessly) costs capacity. A false compatibility (version unchanged but replay-breaking change, for example a helper outside the workflow function that alters step order) can corrupt recovery. The second is the more dangerous failure.

### Conductor licensing

- **[doc]** Self-hosted Conductor is proprietary and requires a paid license for production. A hosted option may have different terms; pricing not verified.
- Conductor would buy automation and an operations UI, **not** fencing.

## 3. Recommendation

**Proceed with DBOS for Phase 1 under the owner-selected at-least-once model, with automatic recovery limited to external effects that are durably idempotent at the receiving boundary. Effects without that property require operator escalation.** Keep Temporal as a documented fallback with explicit kill criteria (section 6). Rationale:

1. The hard problem (dead vs silent) is unsolved in both engines. Semantic safety comes from durable receiving-boundary idempotency for external effects plus checkpoint-level conflict detection, which DBOS provides for its own state. Confirmed termination and leases reduce duplicate exposure or improve availability; they are not the semantic proof.
2. ADR-0038 already puts rediscovery in our system, so the reaper is in scope regardless of engine. The additional build is the version-aware drain controller.
3. Temporal would remove the reaper and drain controller but adds a server cluster, its persistence, and a rewrite of Gate 0.3 work. That cost is not justified unless a blocking test fails.

**Design direction for the reaper (to prototype in Test 5):**

- Stable executor IDs tied to infrastructure identity, so restart-in-place needs no reaper.
- Confirmed termination and leases are availability and duplicate-exposure controls, not the semantic proof. Heartbeat silence or a TTL must not authorise automatic recovery of an effect that lacks durable receiving-boundary idempotency. Any operational takeover control must be tested for its failure behaviour and must not be described as an external execution fence unless that property is independently proven.
- Recovery scoped by application version. A dead executor's runs can only be recovered by a process running that version.
- No session-level advisory locks (transaction-mode PgBouncer). Use compare-and-swap on a lease row for reaper leader election.
- Stable idempotency keys derived from `graft_run_id` and the durable step identity for every automatically recoverable external effect. The receiving boundary must durably honour the key. Long-silent, high-value runs, and all effects without that property, escalate to an operator instead of auto-recovering.
- Prefer public DBOS APIs. If direct system-table reads or writes are needed, record it as a risk and pin the DBOS version.

## 4. Environment and constraints to preserve

- DBOS 3.0.0, locked Python runtime, separate application and system databases, transaction-mode PgBouncer, exactly as in Gate 0.3.
- Every test runs against this topology, not a simplified local setup. If a test needs a simplification, record why and mark the result "reduced fidelity".
- Two-process minimum for all recovery tests, ideally in separate containers.

## 5. Test plan

For each test record: exact commands, environment, raw outputs, pass/fail against the stated criterion, and anything surprising. Store in the Gate 0.3 evidence format (`result.json` plus `commands.json`).

### Blocking tests

**Test 1 — Zombie executor under partition (BLOCKING)**
- Setup: executor A runs a workflow whose step performs an external effect against a stub service that counts calls per idempotency key and also per raw call. Executor B and a prototype reaper are available.
- Steps: pause or partition A (SIGSTOP, and separately a network cut from A to the system DB only) at three points: (a) before the effect, (b) after the effect but before checkpoint, (c) after the last step but before the terminal outcome write. Let the reaper recover on B. Resume A.
- Pass: A's stale checkpoint or outcome write is rejected and A parks or raises the conflict error. The DBOS workflow outcome is recorded once, both handles deliver the same outcome, and no terminal status is overwritten. Raw effect count may be 2 (record it), but the durable receiving boundary applies one effect for the stable key.
- Fail: A's checkpoint or outcome is accepted after B's, outcomes are overwritten, or the conflict error is swallowed silently. **A fail here is a stop-and-escalate.**

**Test 2 — Version-scoped recovery and drain (BLOCKING)**
- Setup: two application versions A (old) and B (new) sharing the system DB, each with running processes.
- Steps: (1) start PENDING and ENQUEUED work on A. (2) Start B and route new traffic to B. (3) Kill an A executor mid-run. (4) Try recovering A's work from a B process. (5) Recover it from a surviving or new A process. (6) Repeat with no A process alive.
- Pass: B cannot recover A's work and A can. With no A process alive, the orphan detector flags the runs (query: PENDING/ENQUEUED whose version has no live executor). Drain completion is detectable as zero PENDING/ENQUEUED for A. Rollback (B→A) was tested with the same drain logic in reverse.
- Fail: work silently stays PENDING with no alert, or B replays A's checkpoints.

**Test 3 — Version hash provenance (BLOCKING)**
Compute the version for each variant and record whether it changed:
- identical source in two separate container builds and two hosts (environment and path sensitivity)
- comment-only and formatting-only edit
- workflow body edit that adds, removes, or reorders a step
- helper function **outside** the workflow that changes which steps run (the dangerous false-compatible case)
- non-DBOS dependency upgrade
- DBOS upgrade with identical app source (two venvs, two DBOS versions), which converts the source-read claim into an observation
- Also record the DBOS source file and function that compute the hash, with the pinned release tag or commit.
- Pass: no environment-dependent versions, and the helper-change result is documented. If helper changes do **not** bump the version, the ADR must state the mitigation (custom version, workflow-source discipline, or a CI check). A DBOS upgrade bumping the version is expected, not a fail.
- Fail: identical source yields different versions across builds or hosts.

**Test 4 — Idempotency contract on Phase 1 side effects (BLOCKING)**
- Inventory every Phase 1 step that performs an external effect. For each, confirm an idempotency key derived from run ID and step exists and is honored by the target (or by our wrapper).
- Run a duplicate-execution test per effect type using the Test 1 harness.
- Pass: every effect has a stable key derived from `graft_run_id` and the durable step identity and the receiving boundary durably honours it, or is explicitly classified as "operator escalation only, never auto-recovered".
- Fail: any effect with no key and no escalation classification. This blocks Phase 1 for that effect.

**Test 5 — Reaper prototype (BLOCKING)**
- Implement the operational design in section 3 minimally: stable executor IDs, any orchestrator-confirmed-death or lease controls, version scoping, CAS lease for reaper leader election, and recovery via the supported DBOS entry point. Do not use TTL or heartbeat silence as the semantic proof for an external effect.
- Verify: two reaper instances never double-recover the same run, a reaper crash mid-recovery is safe to rerun, and it works through PgBouncer with split databases.
- Record effort and any reliance on private DBOS internals.
- Pass: works through public APIs (or documented, pinned exceptions) and no double-recovery.

### Non-blocking (record findings)

- Behavior when recovery attempts are exhausted (dead-letter status, alerting). Verify the exact DBOS 3.0.0 behavior; don't assume.
- Queue behavior across versions: which processes dequeue old-version ENQUEUED work, and do old-version processes keep listening while draining?
- Cancellation of an orphaned run with no live executor.
- Measured drain time from the longest expected Run duration, to size the blue-green overlap.
- Note: a Java SDK issue from September 2026 describes an in-process duplicate execution race in launch-time recovery (https://github.com/dbos-inc/dbos-transact-java/issues/491). It concerns the Java SDK, but check whether the Python SDK has an equivalent window and record the result.

## 6. Decision rules

| Outcome | Action |
|---|---|
| Tests 1–5 all pass | The evidence supports proceeding with DBOS under the at-least-once model. Keep ADR-0076 proposed until the owner reviews the complete evidence and accepts it; do not close Gate 0.3 from this result alone. |
| Test 1 fails | Stop. Escalate. Options: own fencing layer at the checkpoint boundary, or a Temporal spike. Do not proceed to implementation. |
| Test 2 or 3 fails, but a custom application version (supported by DBOS config) fixes it | Adopt a custom version policy derived from declared inputs; update ADR-0046 accordingly; retest. |
| Test 4 fails for an effect | Block that effect from auto-recovery and require operator escalation, or add and prove a durable receiving-boundary idempotency mechanism, before Phase 1 ships it. |
| Test 5 needs private DBOS internals, or the reaper plus drain controller exceeds the agreed effort budget | Price a Conductor license (self-hosted or hosted) and run a time-boxed Temporal spike. Bring both to the decision maker. |

Effort budget for the reaper plus drain controller: **to be set by the decision maker before Test 5 starts. Ask if not provided.**

Whichever way this goes, do not present a Conductor license as a fix for zombie risk. It doesn't provide fencing.

## 7. ADR edits required

1. **ADR-0076:** record the owner-selected at-least-once model. DBOS converges checkpoint and outcome state after duplicate execution but does not fence external execution. Require durable receiving-boundary idempotency with a stable `graft_run_id`/step-derived key for every automatically recoverable effect; effects without it require operator escalation. State that confirmed termination and leases are availability and duplicate-exposure controls, not the semantic proof. Retain proposed status until the recovery barrier/partition matrix, both-handle and concurrent-resume/crash cases, and the Phase 1 effect inventory have results.
2. **Versioning ADR, Context:** stop saying Gate 0.3 "checked" the package-version inclusion unless Test 3 observes it. Separate what was observed, what was read from source, and what is untested.
3. **Versioning ADR, Decision:** split into the decision (accept dependency-upgrade drains) and a separate revisit condition. Give the real safety argument for rejecting "retain the old version" (the version would no longer identify the runtime that wrote the checkpoints). Note that a custom version is a supported config option, and describe the proof required for a custom policy concretely.
4. **Verification section:** split into "verified by experiment", "read from source, not observed", and "not yet tested". Move the decision language to section 2, and do not claim Gate 0.3 closure from the supported-API probe.
5. **Both ADRs:** add the drain-controller requirements: old-version capacity stays up until zero PENDING/ENQUEUED remain for that version, an alert fires on orphaned versions, recovery happens within the same version cohort, and rollback is treated as a reverse drain. Add a rough drain-time estimate.

## 8. Deliverables

1. Evidence files per test (`result.json`, `commands.json`), with a one-line pass/fail/reduced-fidelity verdict each.
2. A results table against section 6, with your recommendation and confidence.
3. The reaper prototype and an effort estimate for productionizing it.
4. Redlined ADR text per section 7.
5. A short list of anything in this brief you found to be wrong or outdated.

## 9. Assumptions and limits of this brief

- This brief comes from vendor documentation and the ADR excerpts, not from running DBOS. **Documentation claims are hypotheses until tested.**
- The `G03-D` evidence file was not seen when this was written.
- Temporal findings were researched lightly (timeout and zombie behavior, worker versioning) and are relevant only if a fallback spike is triggered.
- Conductor and Cloud behavior is cited to explain what we must replicate, not because we intend to use them.

## 10. Sources

- DBOS workflow recovery: https://docs.dbos.dev/production/workflow-recovery
- DBOS self-hosting (executor IDs, admin API recovery, app versions): https://docs.dbos.dev/self-hosting
- DBOS concurrent executions: https://docs.dbos.dev/explanations/concurrent-executions
- DBOS upgrading workflows (versioning, blue-green): https://docs.dbos.dev/python/tutorials/upgrading-workflows
- DBOS Cloud application management (drain and orphan recovery behavior): https://docs.dbos.dev/production/dbos-cloud/application-management
- DBOS self-hosting Conductor (licensing): https://docs.dbos.dev/production/hosting-conductor
- DBOS decentralized workflows (unique-constraint checkpointing): https://www.dbos.dev/blog/scaleable-decentralized-workflows
- Orphaned runs after in-place upgrade (real-world report): https://github.com/czpython/druks/issues/619
- Temporal timeouts and zombies: https://temporal.io/blog/timers-timeouts-and-the-art-of-waiting-in-temporal
- Temporal heartbeat/timeout retry behavior: https://docs.temporal.io/troubleshooting/request-failures
- Temporal worker versioning (pinned workflows, blue-green): https://docs.temporal.io/production-deployment/worker-deployments/recover-pinned-workflows

## 11. Gate 0.3 evidence clarification

The retained Gate 0.3 evidence must not be read as proving more than its
labels state. The former synthetic `recovery_race.py` run is not a DBOS
recovery Test 1, 4 or 5 result: its workflow IDs were absent from DBOS status
rows, so its application-ledger checkpoint and terminal-CAS observations do
not establish DBOS conflict handling. Test 2 is `REDUCED_FIDELITY`/`INCOMPLETE`
because the historical run used private DBOS recovery and a synthetic orphan
detector; the current lane does not use the private operation, and public
`DBOSClient.list_workflows`/`resume_workflows` do not provide an
expected-executor/version conditional takeover. Test 3 remains
`REDUCED_FIDELITY`; an unchanged hash after a helper-only change is
false-compatible, not compatible.

The current `recovery-race.json` is a separate supported-API probe. It records
a real DBOS workflow and step, real migrations and status rows, a keyed HTTP
stub, A stopped with `SIGSTOP` after the effect and before step return, a
same-version worker, a wrong-version worker, and public
`DBOSClient.list_workflows`/`resume_workflow` calls. Its exact observed result
and limitations are evidence; it is not a safe reaper, expected-owner fence,
or general DBOS recovery guarantee. If the public probe cannot complete, the
result is `REDUCED_FIDELITY` and no recovery conclusion is drawn.
