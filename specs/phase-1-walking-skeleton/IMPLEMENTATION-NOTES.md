# Implementation Notes: Phase 1 API-first walking skeleton

> **Date:** 2026-09-17

---

## Summary

Added a runnable, dependency-light API contract/provider core for the Phase 1 walking skeleton. It models private read-only Runs, ordered replayable events, idempotent webhook creation, cancellation boundaries, capability-token validation, curated Tool Gateway calls, and a WSGI HTTP adapter while leaving production DBOS, PostgreSQL, MCP, telemetry, and surface transport integrations behind explicit seams.

## Accepted Gate 0.3 Recovery Scope Boundary

> **Date:** 2026-09-19

Accepted [ADR-0078](../../docs/adr/agent/0078-phase-1-disables-automatic-cross-executor-recovery.md)
records the owner-selected scope change after Gate 0.3. The owner formally
accepted it on 2026-09-19. Phase 1 does not
automatically recover a Run across executor identities. Automatic restart
recovery is limited to a returning matching executor identity and the explicit
released application compatibility revision recorded for the Run. Ambiguous,
alive-but-silent, or stuck Runs are durably recorded and escalated to an
operator. This acceptance fixes the Phase 1 scope boundary; it is not a Phase 1
completion claim.

The accepted trade is explicit: Phase 1 no longer claims recovery after a
worker loss unless the same executor identity returns. Conductor and Temporal
are not selected. The retained Gate 0.3 evidence and the Temporal comparison
spike remain raw historical evidence; neither is rewritten or treated as proof
of a cross-executor recovery fence. Proposed ADR-0076's at-least-once and
receiving-boundary idempotency requirements remain applicable inside the
narrower matching-identity boundary.

The unresolved custom DBOS Test 2 is not required to establish this accepted
Phase 1 boundary. It remains reduced-fidelity research and is not a foundation
for future cross-executor recovery. The retained matrix, partial application-
owned reaper discovery, Conductor commercial/capability record, and Temporal
comparison are indexed in [`evidence/README.md`](evidence/README.md).

## Deviations from the Plan

The plan was auto-generated because no `PLAN.md` existed and was not reviewed by a human. The first implementation deliberately uses an in-memory repository and deterministic model double because the repository has no application package or dependency configuration yet.

## Judgment Calls

- Chose JSON/OpenAPI plus Python dataclasses rather than a framework-specific schema library, so contract tests run on a clean Python installation and the semantic contract stays independent of Grafana or Slack.
- Chose HMAC capability tokens for the local security seam. Production must replace the signer with the approved capability-token authority while retaining the same validation claims and denial behaviour.

## Sanity Checks

| Check | Result | Notes |
|-------|--------|-------|
| `python3 -m unittest discover -s tests -v` | pass | 10 tests passed. |
| `python3 -m compileall -q harness tests` | pass | Python sources compile successfully. |
| Contract JSON parsing | pass | OpenAPI and event schema parse with `json.tool`. |
| `python3 scripts/check_step_pointer_rule.py harness` | pass | 6 Python files checked, 0 errors. |
| `python3 scripts/check_docs.py` | pass after Collector prerequisite | Current local result: 0 errors and 0 warnings. |

## Out of Scope Observations

- Production DBOS recovery, PostgreSQL RLS execution, streamable-HTTP MCP, OTel Collector routing, Langfuse outage tests, and Grafana Live transport cannot be proven without the infrastructure and dependency decisions called out by the spec.

## Remaining Work

AC 6, AC 8, AC 12, AC 15, AC 17, AC 19, and AC 20 remain infrastructure/review work. AC 1–5, AC 9–11, and the local portions of AC 13–14 are covered by the new artifacts and tests. The migration and protocol seams are included so the remaining tests can be added without changing the public contract.


## Gate 0.2 Baseline and Quality Tooling

> **Date:** 2026-09-18

Added the production Python 3.11–3.13 baseline, direct dependency constraints,
development dependency group, `uv.lock`, strict Ruff/mypy/pytest settings,
bootstrap commands, and a commit-pinned GitHub Actions quality workflow. The
workflow covers locked installation, formatting, linting, type checking, unit
tests, the step-pointer architecture rule, documentation, vulnerability
auditing, and licence inventory.

This remains Gate 0.2 work owned by the parent orchestrator. The canonical
Collector prerequisite is recorded below, and the PLAN checkbox is intentionally
unchanged.

## Gate 0.2 Remediation Continuation

> **Date:** 2026-09-18

The quality baseline now applies strict mypy to `harness/`, `scripts/`, and
`tests/`; registers and applies the `unit` and `contract` pytest markers; and
validates JSON field types and labels at runtime. InMemoryStore updates accept
only the intended Run fields and validate their values. The immediate DBOS
experiment's `langchain-mcp-adapters` runtime constraint is locked.

The quality workflow audits an exported locked dependency requirements file
without the local editable project and retains a non-empty licence inventory.
The inventory is evidence only: no allow/deny licence policy is defined. The
inline architecture
check is replaced by `scripts/check_architecture.py`, including the DBOS
`harness/runtime.py` importer rule and direct customer-client boundaries while
leaving generic HTTP clients available for the future Authority Service MCP
client. Documentation CI now watches `deployment/**` and uses read-only
permissions with immutable action pins.

Gate 0.2 remains unchecked. The Collector prerequisite ordering deviation and
its evidence are recorded below; no PLAN checkbox was changed.

## Gate 0.2 Verification Evidence

> **Date:** 2026-09-18

| Command | Expected result | Actual result | Evidence location |
|---------|-----------------|---------------|-------------------|
| `uv lock --check` | Locked dependency graph is current. | Pass. | Local command log. |
| `uv run ruff format --check .` | All tracked source is formatted. | Pass; 121 files already formatted. | Local command log. |
| `uv run ruff check .` | No lint findings. | Pass. | Local command log. |
| `uv run mypy` | Strict typing passes for harness, scripts, and tests. | Pass; 12 source files checked. | Local command log. |
| `uv run pytest -m "unit or contract"` | The selected baseline test suite passes. | Pass; 13 tests passed. | Local command log. |
| `uv run python scripts/check_step_pointer_rule.py harness` | No DBOS pointer-rule violation. | Pass; seven Python files, zero errors. | Local command log. |
| `uv run python scripts/check_architecture.py harness` | No current import-boundary violation. | Pass; seven Python files, zero errors. | Local command log. |
| `uv run pip-audit --strict --disable-pip --requirement /tmp/graft-locked-requirements.txt` | No known vulnerability in the exported locked runtime graph. | Pass; no known vulnerabilities. | Local command log; generated requirements file in `/tmp`. |
| `uv run pip-licenses --format=markdown --with-urls` | A non-empty locked-environment licence inventory is produced. | Pass; the generated local report is non-empty. | GitHub Actions retains `licence-inventory-*` artefacts. |
| `uv run python scripts/check_docs.py` | Zero errors and warnings. | Pass; 0 errors and 0 warnings. | `docs/design/observability-pipeline.md` link check. |

Local verification used Python 3.12.6, uv 0.5.8, Ruff 0.16.8, mypy 2.3.1,
pytest 9.1.1, pip-audit 2.10.1, and pip-licenses 5.5.5. GitHub Actions is
configured to repeat the supported baseline checks on Python 3.11, 3.12, and
3.13. The plan was already present as an untracked file when this work began;
it was preserved and was not regenerated.

## Gate 0.2 Closure

> **Date:** 2026-09-18

The project owner approved the inventory-only licence control and the narrow
Collector prerequisite ordering deviation. Pull request
[`#1`](https://github.com/vikshana/graft-agent-harness/pull/1) then verified
the committed baseline: the documentation workflow passed in 6 seconds and
the `python-quality` matrix passed on Python 3.11 (30 seconds), 3.12 (30
seconds), and 3.13 (34 seconds). The workflow run links are
[`docs`](https://github.com/vikshana/graft-agent-harness/actions/runs/35387574257)
and
[`python-quality`](https://github.com/vikshana/graft-agent-harness/actions/runs/35387574218).

PLAN Gate 0.2 is checked on the basis of that retained CI evidence. Docker was
unavailable locally, so image-level validation of
`otel/opentelemetry-collector-contrib:0.161.0` remains an observability
integration follow-up; it is not claimed by this closure.

## Gate 0.3 Environment Blocker

> **Date:** 2026-09-18

Gate 0.3 is the next unchecked task and cannot be bypassed: it requires real
PostgreSQL and a transaction-mode PgBouncer environment to reproduce DBOS
async, alive-but-silent recovery, executor-filtering, and application-version
behaviour. The local machine has Docker and Colima installed, but the Docker
daemon and Colima are stopped; `psql`, `pg_ctl`, and `pgbouncer` are not
installed. No runnable prior S1/S2 experiment artefacts are in the repository.

The locked current application baseline is DBOS 3.0.0, LangGraph 1.2.11, and
`langchain-mcp-adapters` 0.3.1. Historic design evidence recorded DBOS 2.31.1
and adapter 0.3.2, so Gate 0.3 must record the current resolved versions and
must not represent historical results as reproduction evidence. The four
experiments remain blocked until a disposable local container runtime or an
approved external CI environment is available.

## Gate 0.2 Collector prerequisite

> **Date:** 2026-09-18

By explicit parent-orchestrator approval, this is a narrow ordering deviation:
the canonical Collector prerequisite was created before the later observability
task so the Gate 0.2 documentation check can pass. No PLAN.md or SPEC.md text
was changed, and Gate 0.2 remains owned by the parent orchestrator.

`deployment/otel-collector/config.yaml` is compatible with the pinned
`otel/opentelemetry-collector-contrib:0.161.0` image. It accepts OTLP/gRPC and
OTLP/HTTP, exposes the basic health check, applies bounded memory and batching,
and uses a propagate-mode OTTL scrubber. The scrubber removes common
credential-like attributes from resources, spans, span events and logs, and
replaces every log body. Scrubbed traces are sent to both the operational
OTLP/HTTP exporter and the internal-only Langfuse OTLP/HTTP exporter; metrics and
logs are sent only to the operational exporter. Endpoint, authorisation and
Langfuse ingestion header values are environment expansions only, with bounded
in-memory queues and retries.

PN/PAN detection, sampling policy, and operational endpoint selection remain
explicitly deferred to their owning observability work. No credential literal
was added.

Validation evidence:

| Check | Result | Notes |
|-------|--------|-------|
| `docker run --rm --env ... -v deployment/otel-collector/config.yaml:/etc/otelcol-contrib/config.yaml:ro otel/opentelemetry-collector-contrib:0.161.0 validate --config=/etc/otelcol-contrib/config.yaml` | deferred | Local Docker daemon unavailable; defer to observability integration and do not claim image-level validation. |
| `yamllint -d relaxed deployment/otel-collector/config.yaml` | pass | YAML syntax check passed with no output. |
| `yq eval '.' deployment/otel-collector/config.yaml` | pass | YAML parse check passed with no output. |
| `python3 scripts/check_docs.py` | pass | Local check passed with 0 errors and 0 warnings. |

Follow-up validation evidence for this prerequisite: `yamllint -d relaxed
deployment/otel-collector/config.yaml` passed with no output;
`yq eval '.' deployment/otel-collector/config.yaml >/dev/null` passed with no
output; and `uv run python scripts/check_docs.py` passed with `0 error(s), 0
warning(s)`. Docker was not available: `docker version --format
'{{.Server.Version}}'` and the pinned-image validation command both returned
`failed to connect to the docker API at unix:///var/run/docker.sock; check if
the path is correct and if the daemon is running: dial unix /var/run/docker.sock:
connect: no such file or directory`. Therefore the exact
`otel/opentelemetry-collector-contrib:0.161.0` binary validation is deferred
until Docker access is available; it was not marked as passed.

## Gate 0.2 Evidence Correction

> **Date:** 2026-09-18

The project owner explicitly approved the current non-empty locked-environment
licence inventory as an inventory-only control. No allow/deny licence policy is
defined, and this is not treated as a Gate 0 blocker. The owner also approved
the narrow ordering deviation that created the canonical Collector prerequisite
before the later observability task. The plan checkbox remains unchanged.

After that prerequisite was created, local `uv run python scripts/check_docs.py`
verification passed with 0 errors and 0 warnings. The earlier baseline entries
above record the state before the prerequisite and are retained as historical
evidence, not as the current result.

The local Docker daemon remains unavailable. Image-level validation against
`otel/opentelemetry-collector-contrib:0.161.0` is therefore deferred to
observability integration and is not claimed here.

## Gate 0.3 DBOS experiment harness

> **Date:** 2026-09-18

Added a bounded, throwaway experiment under `deployment/gate-0.3/` with only
PostgreSQL 16 application/system databases and transaction-mode PgBouncer. The
runner generates synthetic local runtime credentials into an ignored `.env`,
never embeds real secrets, has no customer-system access, and writes redacted
JSON evidence under `specs/phase-1-walking-skeleton/evidence/gate-0.3/`.

The `gate_0_3` marker is registered separately from the fast `unit` and
`contract` markers. Fast CI's `-m "unit or contract"` expression therefore does
not silently run container experiments.

The runner targets DBOS 3.0.0 from the lock and records dependency/runtime
versions and exact commands. It covers async DBOS decorated steps, a no-
checkpointer LangGraph capability boundary, streamable-HTTP MCP client
construction, executor-id `list_workflows` filtering without Conductor, and
same-source application-version stability plus source-change hashes. The
isolated synthetic idempotency exercise is explicitly not alive-but-silent
recovery proof. Public DBOS APIs do not safely prove alive-but-silent recovery;
that question remains unresolved, and a timeout is not treated as proof.

Gate 0.3 remains unchecked. Parent validation owns the container run and the
interpretation of all experiment evidence.


## Gate 0.3 evidence correction and supported-API probe

> **Date:** 2026-09-19

The retained Gate 0.3 artefacts are evidence inputs, not closure evidence.
Their interpretation is corrected here once, without changing the plan,
specification, ADRs, design documents, production harness, or workflows.

| Area | Correct interpretation |
|------|------------------------|
| G03-A, G03-C and G03-D | The earlier bounded observations remain limited to the behaviours recorded in `result.json`; they do not establish recovery ownership. |
| Tests 1, 4 and 5 | `recovery-race.json` is not a DBOS recovery Test 1, 4 or 5 result. The former `recovery_race.py` run was a synthetic application-ledger race whose workflow IDs were absent from DBOS `workflow_status`; its keyed-effect and terminal-CAS counts therefore cannot prove DBOS checkpoint or terminal conflict handling. |
| Test 2 | `test-2-result.json` is `REDUCED_FIDELITY`/`INCOMPLETE`. The historical run invoked private DBOS recovery and used a synthetic orphan detector. The current worker does not invoke private recovery. Public `DBOSClient.list_workflows` and `DBOSClient.resume_workflows` cannot express an expected-executor/version conditional takeover, so no cross-executor recovery conclusion is claimed. |
| Test 3 | `test-3-result.json` remains `REDUCED_FIDELITY`. The helper-only unchanged hash is explicitly a false-compatible result, not compatible behaviour. Dependency-upgrade probes were blocked, so no cross-DBOS-version result is claimed. |

The decisive follow-up is the narrow `recovery_race.py` supported-API probe. It
uses a real DBOS workflow and decorated step, a keyed HTTP effect stub, real
DBOS migrations and status rows, `SIGSTOP` after the effect and before the
step returns, a same-version worker, a wrong-version worker, and only public
`DBOSClient.list_workflows`/`DBOSClient.resume_workflow` calls. It records the
exact result in [`recovery-race.json`](evidence/gate-0.3/recovery-race.json)
and commands in
[`recovery-race-commands.json`](evidence/gate-0.3/recovery-race-commands.json).

The probe is not allowed to claim a safe reaper, expected-owner fencing, or a
general DBOS recovery guarantee. If the public API cannot safely drive the
scenario, its verdict is `REDUCED_FIDELITY` and the failure is recorded. No
private DBOS API and no DBOS system-table mutation is permitted. Parent
validation owns the Docker run, final interpretation, and gate status.

## Supported-API zombie-race result

> **Date:** 2026-09-19

The real DBOS 3.0.0 post-effect/pre-checkpoint race used public
`DBOSClient.list_workflows` and `DBOSClient.resume_workflow`, with a synthetic
keyed HTTP receiver. The original executor was stopped after its first raw
effect; the same-version replacement completed the Run; when the original
executor resumed, DBOS reported duplicate execution and converged on the
recorded result. The receiver saw two raw calls for one Run/step-derived key
and applied one keyed effect. This establishes **at-least-once external
execution plus receiver-side idempotency and DBOS checkpoint/outcome
convergence**. It does not establish exactly-once execution or an executor
fence.

The remaining evidence is deliberately limited. The wrong-version worker was
not given the public resume operation while it was the only possible recovery
worker, so no version-scoped recovery inference is claimed. The complete
barrier/partition matrix, both-handle outcomes, concurrent resume/crash cases,
and the Phase 1 effect inventory remain required. Proposed ADR-0076 therefore
needs reframing around durable idempotent effects and operator escalation for
effects that cannot be made idempotent; confirmed termination and leases reduce
duplicate exposure but are not the semantic safety guarantee. Proposed ADR-0077
now records the accepted ADR-0077 decision superseding ADR-0046: every mutually
versioned release receives an explicit released application compatibility
revision, every prior release cohort drains, and the value is not a mutable Git
SHA or image tag. The Gate 0.3 version matrix found a false-compatible
helper-only change and a direct DBOS-version change, but did not exercise
operational draining, orphan alerts, matching-version recovery, or reverse-drain
rollback. Operational drain evidence remains a separate Gate 0.3 follow-up.

## Gate 0.3 recovery decision revision

> **Date:** 2026-09-19

The project owner selected the at-least-once recovery model for proposed
ADR-0076. DBOS may execute a step more than once; it converges the checkpoint
and Run outcome after duplicate execution, but it does not fence the external
execution. Every automatically recoverable external effect must therefore be
durably idempotent at the receiving boundary, with a stable idempotency key
derived from `graft_run_id` and the durable step identity. An effect without
that property is not automatically recoverable and requires operator
escalation. Confirmed termination and leases remain availability and duplicate-
exposure controls, not the semantic proof of effect safety.

ADR-0076 remains **proposed**. The supported-API zombie-race observation is not
an engine-level external-effect fence. The later bounded matrix and effect
inventory completed the following evidence lanes without changing the ADR-0076
or Gate 0.3 status:

| Evidence lane | Current status |
|---|---|
| Recovery barrier/partition matrix: before effect, after effect before checkpoint, and after the final step before outcome write, including the system-database network cut | Bounded matrix retained; not a DBOS executor fence |
| Both-handle outcomes plus concurrent resume and crash cases | Bounded public-API and application-reaper observations retained |
| Phase 1 external-effect inventory, with receiving-boundary idempotency tests and an explicit operator-escalation classification for every non-idempotent effect | Inventory retained; currently unimplemented or unverified effects remain `B`/operator escalation |
| Custom DBOS Test 2: expected-executor and released-revision conditional takeover | `REDUCED_FIDELITY`/`INCOMPLETE`; not required to establish accepted ADR-0078 and not a foundation for future cross-executor recovery |

Gate 0.3 remains unresolved as an implementation/evidence gate, and Gate 1
remains blocked by its remaining checks. This is separate from the accepted
ADR-0078 scope boundary and does not make custom Test 2 a required condition for
that boundary. ADR-0077 is accepted; its operational evidence remains
outstanding for the all-release drain, including `PENDING`, `ENQUEUED`, and
`DELAYED` drain checks, orphan alerts, matching-version recovery, and
reverse-drain rollback.

## Gate 0.3 DBOS version-comparison lane

> **Date:** 2026-09-19

The bounded ADR-0077 experiment lane added a real isolated comparison of DBOS
2.31.1 and 3.0.0. It used `uv run --isolated --no-project` for every worker,
did not read or modify the project lock, and ran Python 3.11, 3.12 and 3.13
for each DBOS version. The two cohorts used separate disposable PostgreSQL 16
containers, databases and DBOS system schemas:

| Cohort | DBOS | PostgreSQL database | DBOS system schema | Python results |
|--------|------|---------------------|--------------------|----------------|
| old | 2.31.1 | `gate03_dbos_2311_system` | `dbos_2311` | 3.11.11, 3.12.6, 3.13.0 |
| locked | 3.0.0 | `gate03_dbos_300_system` | `dbos_300` | 3.11.11, 3.12.6, 3.13.0 |

Both cohorts launched the same minimal registered workflow with application
name `gate-0-3-db-version-compare`. The actual DBOS launch/runtime fields
recorded automatic application version `c794758e9a435661e8952586635ba345`
for 2.31.1 and `469124d570d40494405ef8ad74749acb` for 3.0.0, stable across
the three Python variants. Each workflow completed `SUCCESS`. This directly
establishes, rather than infers from source, that changing DBOS from 2.31.1 to
3.0.0 changes the automatic application version even when workflow source and
application name are unchanged.

The same runtime lane also launched DBOS 3.0.0 with helper-only variants in
separate processes and the same application name. The baseline returned
`helper-v1:gate-0-3-version-fingerprint`; the changed helper returned
`helper-v2:gate-0-3-version-fingerprint`. Both actual launch/runtime records
reported `6291bf83d0ad38ca22f83e659454e749`. This is an observed
false-compatible result: helper code changed and runtime output changed while
the automatic version did not. It is explicitly distinct from the existing
source-only probe; no LangGraph upgrade test was claimed or added.

The exact redacted result, resolved distributions, runtime fields, migration
records, result fingerprints and commands are retained in
[`evidence/gate-0.3/dbos-version-comparison-result.json`](evidence/gate-0.3/dbos-version-comparison-result.json)
and
[`evidence/gate-0.3/dbos-version-comparison-commands.json`](evidence/gate-0.3/dbos-version-comparison-commands.json).
The DBOS 2.31.1 system database recorded migration 108; the DBOS 3.0.0
system database recorded migration 114. Each also recorded its own DBOS tables
in its own schema; the containers and volumes were removed after the run. The
migration records are observations from separate launches, not an operational
drain test or cross-version recovery test: no workflow was drained or recovered
between DBOS versions, and rollback was not exercised. The lane status is
`passed` for its direct application-version comparison. On the basis of the
helper false-compatibility result, the owner selected the proposal in ADR-0077
to supersede ADR-0046 with an explicit released compatibility revision for
every mutually versioned release and an all-prior-cohort drain. The explicit
value is not a mutable Git SHA or image tag. Operational drain evidence remains
outstanding; Gate 0.3 remains
subject to the parent orchestrator's decision and other outstanding safety
evidence.

## ADR-0077 formal acceptance

> **Date:** 2026-09-19

The project owner formally accepted [ADR-0077](../../docs/adr/agent/0077-auto-versioning-must-account-for-dependency-upgrades.md),
which supersedes ADR-0046 and requires an explicit released application
compatibility revision for every mutually versioned release plus an
all-prior-cohort drain. This records acceptance of the decision only. The
operational drain evidence remains outstanding, and Gate 0.3 remains
unresolved while Gate 1 remains blocked by the outstanding recovery and effect
evidence; no gate or implementation completion is claimed.

The earlier sentence stating that ADR-0077 remained proposed is superseded by
this dated acceptance entry. It is retained above as historical evidence of
the pre-acceptance state; no operational drain or Gate 0.3 completion is
claimed.

## Gate 0.3 recovery barrier matrix and effect inventory

> **Date:** 2026-09-19

The supported-API recovery lane was expanded under `deployment/gate-0.3/` and
run against the disposable PostgreSQL 16 application/system topology with
transaction-mode PgBouncer present. It uses DBOS 3.0.0 from the locked
environment, real DBOS migrations, public `DBOSClient.list_workflows` and
`DBOSClient.resume_workflow`, public workflow-handle `get_result`/`get_status`,
and no DBOS system-table reads or writes. Redacted output is retained in
[`evidence/gate-0.3/recovery-race.json`](evidence/gate-0.3/recovery-race.json)
and its command record.

The three SIGSTOP barrier cases and the executor-specific system-database
partition completed as `PASS` for this bounded matrix:

| Barrier | Raw receiver calls | Keyed effects | Final public status | Public result comparison |
|---|---:|---:|---|---|
| Before effect | 2 | 1 | `SUCCESS` | scenario B |
| After effect, before step checkpoint | 2 | 1 | `SUCCESS` | scenario B |
| After final step, before workflow outcome | 1 | 1 | `SUCCESS` | scenario B |
| Post-effect with A-only system-network cut | 2 | 1 | `SUCCESS` | scenario B |

Each case also ran two concurrent public resume attempts and killed a reaper
after public resume acceptance while the status was non-terminal, followed by
a public retry. The receiver's
automated assertions verified that every raw call used the stable
`graft_run_id:durable_step_id` key and that raw/keyed counts were preserved.
The raw duplicate in the first two cases is expected under the selected
at-least-once model; the single keyed application is a property of the
synthetic receiving boundary only.

The local topology now uses a separate `gate03-system` Docker network. The
partition disconnects only executor A; executor B and the reapers retain their
DBOS system-database path. The final public status asserts `executor_id` equals
the run-unique scenario-B executor ID. Containers are removed after each
scenario, preventing stale executor contamination.

The explicit Phase 1 effect inventory is retained in
[`evidence/gate-0.3/phase-1-effect-inventory.json`](evidence/gate-0.3/phase-1-effect-inventory.json).
Every currently unimplemented or unverified effect is now classification `B`
with operator escalation. Its distinct `promotion_criteria` field describes
the evidence required before a later candidate classification `A`. The
inventory covers the current PLAN/spec phase scope and reference prototype and
does not claim support for Grafana, Kubernetes, an LLM provider, or any other
real customer system. The synthetic service's contract is also checked by
`tests/gate_0_3/test_gate_0_3_config.py`.

This lane remains evidence only. It does not change Gate 0.3 status or
ADR-0076 status.

## Gate 0.3 oracle blocker correction

> **Date:** 2026-09-19

The container matrix was extended with an application-owned reaper prototype.
Each run has unique executor IDs; A, B and reapers are distinct containers;
the system database uses the separate `gate03-system` network; and only A is
disconnected for the partition case. The matrix records successful fault
injection and reconnect commands, A/B public handle events, B ownership of the
terminal status, public concurrent resumes, and a reaper crash after accepted
resume while the status is non-terminal. The reaper uses a stable reaper ID,
explicit application revision, and a compare-and-swap lease in the application
database through transaction-mode PgBouncer. It uses public DBOS APIs only and
does not read or write DBOS system tables. Actual elapsed effort is retained as
`effort_elapsed_seconds` per scenario.

The local rerun produced `PASS` for the four bounded recovery scenarios, but
the evidence remains bounded and does not accept ADR-0076 or Gate 0.3. The
original A handle events and the winning B handle events are now captured; if
either cannot be observed, the scenario fails rather than fabricating a pass.

Test 2 remains `REDUCED_FIDELITY`: the report now uses distinct explicit
release revisions, records `PENDING`, `ENQUEUED` and `DELAYED`, forward and
reverse drain, orphan observations and matching-revision replacement attempts.
The exact blocker remains that public DBOS APIs cannot safely condition resume
on an expected executor and application revision. No accepted ADR-0077 drain
claim is made.

Test 3 remains `REDUCED_FIDELITY`. Its dependency probes remain blocked and its
helper-only result remains explicitly false-compatible; no version-comparison
pass claim is inferred from those blockers.

The Gate 0.3 workflow now pins action SHAs, runs the container recovery report,
the async/MCP and executor-listing reports, Test 2/Test 3, Gate 0.3 tests and
the relevant project quality checks. It fails nonzero for an incomplete
mandatory recovery report and retains redacted evidence. Gate 0.3 and
ADR-0076 status are unchanged.

The final local rerun on 2026-09-19 produced `PASS` for all six container
recovery scenarios. It recorded executor-A-only partition/reconnect success,
original A and winning B handle observations, two concurrent public resumes,
reaper crash/retry, explicit application revision selection, CAS lease backend
through transaction PgBouncer, and elapsed effort per scenario. The separate
Test 2 rerun produced `REDUCED_FIDELITY` with explicit revisions, all three
active states, forward/reverse drain and orphan observations; its exact public
API revision-selection blocker remains recorded. Test 3 remains
`REDUCED_FIDELITY` with blocked dependency probes and the false-compatible
helper result. Test 3 is `PASS_WITH_ADR_0077_MITIGATION` for policy purposes;
the reduced-fidelity observations remain retained and are not automatic-hash
proof.

## Conductor commercial and capability evidence

> **Date:** 2026-09-19

Added the dated, documentation-only Conductor commercial and capability record
at [`evidence/conductor-evaluation/2026-09-19-conductor-commercial-capability-evidence.md`](evidence/conductor-evaluation/2026-09-19-conductor-commercial-capability-evidence.md).
It records the official public DBOS Pro and Teams prices, Enterprise and
self-hosted pricing unknowns, key and configuration requirements, documented
recovery scope, and the explicit non-claim that Conductor fences external
effects. It also retains a complete vendor quote/question checklist and the
criteria required before comparing Conductor with owned recovery controls or a
fallback engine.

The record preserves unknowns and does not claim a quote, purchase, trial,
trial key, vendor response, production entitlement, or Conductor deployment.
Official source URLs in the record were checked on 2026-09-19. No ADR, design,
roadmap, PLAN, SPEC, code, or workflow file was changed for this evidence lane.

## Gate 0.3 closure

> **Date:** 2026-09-20

The accepted-scope report suite passed locally and in GitHub Actions after the
accepted ADR-0078 recovery boundary was applied. The retained workflow is
[`Gate 0.3 container recovery matrix`](https://github.com/vikshana/graft-agent-harness/actions/runs/35497301859)
for commit `6c859b9b0b5fb32aabed7ad4822df640f0183943`: its pinned Python 3.13.0
job passed PostgreSQL/PgBouncer startup, all four canonical reports, the Gate
0.3 test suite, quality checks, and redacted evidence upload.

Canonical reports are retained in `evidence/dbos/`: async LangGraph/MCP,
matching-executor/revision restart plus durable operator escalation,
executor-filtered listing, and explicit compatibility-revision/versioning.
Cross-executor recovery remains deferred research only and is not interpreted
as Phase 1 evidence. Gate 0.3 is checked; Gate 1 begins with the contract
authority task.

## Bounded Temporal comparison spike

> **Date:** 2026-09-19

Added a disposable comparison lane under `deployment/temporal-spike/`, with
static checks under `tests/temporal_spike/` and redacted runtime evidence under
`evidence/temporal-spike/`. It is deliberately not a product implementation,
does not change the selected DBOS engine, has no customer-system client, and
does not deploy to production. The `temporal_spike` pytest marker keeps it out
of the default `unit or contract` expression.

The lane pins `temporalio/auto-setup:1.29.1` and `postgres:16.8-alpine` by
resolved digest, uses synthetic local-only database credentials, and uses the
Python SDK `temporalio==1.20.0` in the gated `temporal-spike` dependency group.
The exact compose, SDK, runner, and cleanup commands are retained in
`evidence/temporal-spike/commands.json`.

The local run classified the lane `PASS_WITH_LIMITATIONS`: a hard worker death
was followed by retry with heartbeat/timeout evidence; a post-effect death
produced two raw receiver deliveries but one keyed logical effect; and the
current SDK/server combination recorded a `workflow.patched` marker that passed
the SDK replay check. These observations do **not** mean Temporal fences
external effects. The synthetic receiver's durable key is what collapsed the
duplicate logical effect; Temporal still permits at-least-once activity
execution when a worker is dead or merely silent.

The selected SDK/server also emitted a warning that runtime worker heartbeating
is unsupported, while activity heartbeats and the server-side heartbeat timeout
were observed and classified separately in `result.json`; this is not treated
as runtime-heartbeat support.

The evidence explicitly does not cover DBOS step trajectories,
`list_workflow_steps`, `fork_workflow` evaluation replay, partition-key queue
flow control, the DBOS PostgreSQL system-database/pooler topology, or the DBOS
executor/reaper and released compatibility-revision policy. This is comparison
evidence only, not a decision to switch engines.

## Gate 0.3 accepted-scope closure repair

> **Date:** 2026-09-20

Repaired only the accepted Gate 0.3 closure defects. The accepted recovery
experiment now has one `accepted_runtime_recovery` entry point. It reads
insert-once Run metadata, rejects conflicting application revisions, rejects
wrong executor identity and released application compatibility revision before
calling public DBOS resume, and records typed durable `ALIVE_BUT_SILENT`,
`AMBIGUOUS`, and `STUCK` operator escalation rows. Matching executor and
revision restart evidence is retained separately from the negative cases.
This is the accepted [ADR-0078](../../docs/adr/agent/0078-phase-1-disables-automatic-cross-executor-recovery.md)
boundary and uses the released-revision requirements of
[ADR-0077](../../docs/adr/agent/0077-auto-versioning-must-account-for-dependency-upgrades.md);
it does not claim automatic cross-executor recovery.

Reports 02, 03, and 04 now distinguish observations from accepted policy
requirements. Version-comparison cleanup preserves the compose environment
needed by the main topology, and CI retains both `evidence/dbos/` and
`evidence/gate-0.3/` for 14 days. `actionlint` and the Gate 0.3 static/report
tests pass locally. Docker accepted reports and the full local quality checks
were run against the disposable PostgreSQL 16 and transaction-mode PgBouncer
topology. GitHub Actions itself has not run here, so CI cannot yet be called
passing locally. Gate 0.3 remains unchecked in `PLAN.md`.

## Gate 0.3 final accepted-evidence reproducibility repair

> **Date:** 2026-09-20

The accepted report lane now executes the shared async/MCP/listing source
experiment once for `accepted_scope_reports.py all`, and records the exact
source-artifact path and SHA-256 in reports 01 and 03. A `PASS` requires the
actual async `SUCCESS`, the false LangGraph checkpointer, the exact decorated
step list, a real synthetic streamable-HTTP MCP response, the injected MCP
failure, and the exact positive/negative executor filters. Partial or blocked
source evidence is `INCOMPLETE`, never `PASS`.

Report 04 records the observed DBOS 2.31.1 and 3.0.0 automatic-version values,
the migration observations, and the helper-only false-compatible runtime
observation. Its lane is explicitly private/source/schema diagnostic evidence,
not public API behaviour. ADR-0077 requirements are under a separate policy
field and are not presented as observations.

The isolated comparison now uses Python 3.11.11, 3.12.6 and 3.13.0 and exact
dependency versions, while the Docker probe uses a digest-pinned interpreter
image and exact dependency versions. The local Docker rerun completed the four
accepted reports with `PASS`; the retained canonical reports and raw Gate 0.3
artefacts cross-link the shared result and version-comparison evidence.
`uv run pytest -m gate_0_3 tests/gate_0_3` passed all 15 tests, Ruff format and
lint passed for the Gate 0.3 scope, and `actionlint .github/workflows/gate-0-3.yml`
passed. The workflow runs both Gate 0.3 test modules and retains both evidence
directories. No plan task was checked.

## Bounded Gate 1 Task 1 — contract authority artefacts

> **Date:** 2026-09-20

Implemented the bounded contract task without changing the WSGI adapter,
service, store, security, design, ADR or specification files, and without
adding the Gate 2 MCP server. The checked-in contract authority now includes:

- the complete v1 REST operation set for Run creation, retrieval, exclusive
  event replay/follow semantics, and cancellation;
- typed standard authentication, authorisation, validation, unsupported
  version, not-found, idempotency, state, cursor, retention, throttling,
  timeout, dependency and server-error envelopes;
- the full v1 event taxonomy from the streaming design, typed payload variants,
  additive unknown-event/unknown-field rules, exclusive `graft_event_id`
  cursors, and pointer-only external result references;
- a versioned harness-owned MCP v1 capability manifest and schema containing
  only Run tools/resources, the two Run URI templates, declared MCP tools and
  resources capabilities, and an explicit future authentication placeholder.
  It declares no Tool Gateway or customer-system capability, no DCR policy,
  and no production identity implementation;
- independent provider and transport-neutral consumer tests, every event
  variant and error example, additive and breaking compatibility fixtures,
  pointer-only checks, and semantic cursor/idempotency/Tenant tests; and
- `scripts/check_contracts.py` plus the Python quality workflow invocation.

The reference provider remains deliberately labelled as a synchronous,
in-memory prototype. Its canonical `to_contract_dict()` representations are
available for the future Authority Service composition, while its legacy
`to_dict()` shape remains for the retained WSGI tests. This is not evidence of
production Authority Service identity resolution: that profile remains
implementation-pending, as does the Gate 2 streamable-HTTP MCP adapter.

Validation evidence for this bounded task:

| Check | Result |
|-------|--------|
| `uv run pytest -m "unit or contract"` | pass; 27 tests |
| `uv run pytest` | pass; 46 tests |
| `python3 scripts/check_contracts.py` | pass; REST, event, MCP, examples and compatibility fixtures |
| JSON parsing for all four contract artefacts | pass |
| `uv run ruff format --check .` | pass |
| `uv run ruff check .` | pass |
| `uv run mypy` | pass; 20 source files |
| `python3 -m compileall -q harness tests scripts` | pass |
| `uv run python scripts/check_docs.py` | pass; 0 errors and 0 warnings |

The Gate 1 Task 1 checkbox is intentionally unchanged here. Parent validation
owns the final decision because production identity authority, the actual
inbound MCP adapter, and infrastructure-backed transport evidence remain
future work; this bounded change does not claim those behaviours.

## Gate 1 Task 1 contract defect repair

> **Date:** 2026-09-20

Independent review defects in the bounded contract lane were repaired without
changing service, store, security, specification, ADR, design, or MCP-server
implementation files. The contract checker now compares the live REST/event/
MCP signature against the preserved `tests/fixtures/contract-baseline.json`.
It executes additive and breaking mutations: required-field removal, type and
semantic changes, operation removal, URI/cursor changes, and additive fields,
payloads, events, and resources. JSON Schema validation covers REST examples,
event examples, MCP manifest examples, and model serialisations when the
locked `jsonschema` dependency is available.

The reference WSGI provider now accepts canonical graft-prefixed REST inputs
and emits canonical `EventReplayPage`, Run, cancellation, and error envelopes.
Its `VerifiedIdentity` value is an explicitly named, test-only, out-of-band
composition seam; request bodies and HTTP headers cannot supply trusted
`graft_tenant_id` or `graft_principal_id`. Production Authority Service
identity resolution remains pending Gate 1 Task 2. MCP is declared
streamable-HTTP only, with REST-equivalent idempotency and exclusive cursor
semantics in the manifest. Pointer-only tool-result validation rejects inline
raw/result/content fields while allowing additive non-sensitive fields.

The Task 1 checkbox remains intentionally unchanged. This repair does not
claim Authority Service implementation, an inbound MCP transport, production
authentication, or pending provider operation variants.

Validation evidence for this repair:

| Check | Result |
|-------|--------|
| `uv run ruff format --check .` | pass |
| `uv run ruff check .` | pass |
| `uv run mypy` | pass; 20 source files |
| `uv run pytest -m "unit or contract"` | pass; 33 tests |
| `uv run pytest` | pass; 52 tests |
| `uv run python scripts/check_contracts.py` | pass; baseline mutations, REST/events/MCP examples, and model-independent checks |
| `uv run python scripts/check_docs.py` | pass; 0 errors and 0 warnings |

The contract checker emits only a dependency deprecation warning from the
installed `jsonschema.RefResolver`; it does not affect the passing result.
Parent validation owns the final Gate 1 decision and must leave the plan task
unchecked if any future provider or authority claim cannot be verified.

## Gate 1 Task 1 oracle blocker repair

> **Date:** 2026-09-20

Repaired the final Task 1 contract blockers within the permitted contract and
reference-provider scope. Modified files are the REST/OpenAPI, event, and MCP
contract artefacts; `harness/contracts.py`, `harness/http_api.py`, and
`harness/service.py`; the contract checker and compatibility fixtures; the
contract, consumer, and provider tests; and the Python quality workflow.
`PLAN.md`, ADRs, design documents, MCP server implementation, and Authority
Service implementation were not changed.

The canonical REST create requires `X-Graft-Idempotency-Key`; the MCP create
requires `graft_idempotency_key`; both reject caller identity. MCP input,
output, supported-error, cursor, cancellation, and resource mappings are
checked against the REST operation rather than only matching operation names.
The compatibility signature now follows nested `$ref`, `items`, and composed
schemas, all MCP input/output schemas, REST parameters/responses/security and
provider status, and resource template details. Required removals, narrowed
enums, type/meaning changes, operation removals, and resource changes fail;
new optional fields, tools, resources, and event types remain additive under
the documented policy. Fixtures execute these mutations.

The WSGI adapter is explicitly a reference provider. Its canonical create,
cancel body, replay mode, unsupported-version mapping, cursor errors, and
request correlation are tested. The old body spelling is retained only for
the existing synchronous unit adapter and is labelled legacy in the tests;
canonical requests cannot use it. Live follow streaming and unimplemented
standard infrastructure error outcomes remain declared implementation-pending
or outside provider-supported coverage rather than being falsely claimed.
MCP examples now validate call inputs, every tool output, protocol/tool
errors, resources, resource results, and event examples. Tool-call result
payloads and external references are closed pointer-only schemas; inline
`graft_blob`, raw, result, and content fields are rejected while additive
fields/events elsewhere remain tolerated.

Final local validation for this repair: `uv run pytest` passed (56 tests),
`uv run python scripts/check_contracts.py` passed, Ruff format and lint passed,
strict mypy passed (20 source files), compileall passed, and
`uv run python scripts/check_docs.py` passed with 0 errors and 0 warnings.
The Gate 1 Task 1 checkbox remains intentionally unchecked for parent review.

## Gate 1 Task 1 pointer and additive-policy closure

> **Date:** 2026-09-20

The final contract repair closes every pointer-bearing event payload shape:
`ToolCallResultPayload`, `PointerPayload`, `EvidencePayload`, and the shared
external-reference shape reject inline raw, large, blob, content, and result
fields in both JSON Schema and the dependency-free Python models. They retain
only identifiers, external pointers, and the explicitly defined safe pointer
metadata extension. Event examples and consumer/provider tests exercise the
closed boundary and reject representative inline fields.

The v1 compatibility policy is deliberately asymmetric. The global event
envelope, unknown event types, and additive fields on tolerant non-sensitive
payloads remain forward-compatible and are ignored by consumers. Closed,
security-sensitive pointer/reference payloads cannot gain inline payload fields
within v1. Adding a safe pointer metadata field requires an explicit reviewed
schema additive change or the defined `graft_pointer_metadata` extension
mechanism; it is not a generic additive-field exception.

The MCP manifest follows the same policy. Existing Tool and Resource
declarations and their closed input/output/reference shapes are not generic
additive surfaces. New Tool or Resource entries are additive, and an existing
declaration may use only the explicitly defined extension-safe metadata object.
The compatibility checker classifies additions to closed pointer/reference
payloads and existing MCP declarations as breaking rather than generic
additive changes, while preserving tolerant envelope and unknown-event rules.

The Gate 1 Task 1 checkbox remains intentionally unchecked. This repair closes
the contract pointer/additive-policy defects only and does not claim the
separate production identity, PostgreSQL, Authority Service, or inbound MCP
implementation gates.

## Gate 1 Task 1 contract closure (local evidence)

> **Date:** 2026-09-20

The final independent review found the Task 1 local done condition satisfied.
The contract foundation covers canonical REST, event and harness-MCP schemas;
typed pointer-only payloads; complete declared error mappings; executable
additive and breaking compatibility fixtures; and transport-neutral REST/MCP
semantic parity. The reference WSGI provider uses only an explicit test verified
identity seam. Authority Service identity resolution and the inbound
streamable-HTTP MCP adapter remain later work and are not claimed here.

Local evidence: `uv run pytest` passed 66 tests; `uv run python
scripts/check_contracts.py`, Ruff, strict mypy, documentation, architecture,
step-pointer, JSON parsing, locked dependency audit, and licence inventory all
passed. The checker applies mutations to actual signatures: ordinary optional
Run output fields shared through MCP are additive, while closed pointer/reference
payload changes, removed required fields, and transport drift fail. The Task 1
checkbox is updated pending the matching remote Python-quality CI evidence.

## Gate 1 Task 1 contract closure (CI evidence)

> **Date:** 2026-09-20

The repository Actions policy was updated to permit GitHub-created actions with
full-commit SHA pinning after the earlier pre-job policy rejection. The fresh
[`python-quality` run](https://github.com/vikshana/graft-agent-harness/actions/runs/35505627112)
passed on Python 3.11, 3.12, and 3.13 for commit
`adb9c4f9322eab103f10db46e36f6dd7479a115e`. Each matrix job passed the
contract artefact check, formatting, linting, strict typing, unit/contract
tests, architecture/pointer/documentation checks, strict vulnerability audit,
and retained licence inventory. Gate 1 Task 1 is checked on that retained CI
evidence.

## Gate 1 Task 1 CI policy remediation

> **Date:** 2026-09-20

The first remote `python-quality` run for the contract commit failed before any
job started because repository Actions policy allowed only `vikshana`-owned
actions. It was not a workflow or contract-test failure: GitHub rejected the
already SHA-pinned `actions/checkout`, `actions/setup-python`, and
`actions/upload-artifact` actions at startup. The project owner changed the
repository policy to permit GitHub-created actions while retaining full-commit
SHA pinning. The failed run cannot be retried, so Task 1 remains unchecked until
a fresh Python-quality run provides retained evidence.

The subsequent Python 3.11–3.13 matrix passed for the initial contract commit.
Final compatibility and pointer-policy repairs followed that commit, so the
Task 1 checkbox remains unchecked until a fresh matrix validates the final
contract state.

## Gate 1 Task 1 contract closure (final CI evidence)

> **Date:** 2026-09-20

The final contract revision was validated by the fresh
[`python-quality` run](https://github.com/vikshana/graft-agent-harness/actions/runs/35505892089)
for commit `8c4da115c2026c646365ff5138da7911c6152747`. Python 3.11, 3.12,
and 3.13 all passed formatting, linting, strict typing, tests, the executable
contract artefact/compatibility checker, pointer and architecture checks,
documentation, vulnerability audit, and retained licence inventory. Gate 1
Task 1 is checked on that retained CI evidence.

## Gate 1 Task 2 — proposed internal identity-resolution decision

> **Date:** 2026-09-20

Added proposed [ADR-0079](../../docs/adr/identity/0079-internal-surface-credential-resolution-uses-mtls-and-typed-decisions.md)
for the concrete Harness API → Authority Service Token Service boundary. It
requires an mTLS-only internal endpoint, verbatim forwarding of the opaque raw
surface credential, an explicit surface discriminator, and a canonical
normalised webhook envelope that is separate from the credential. The Token
Service, rather than the Harness API, resolves and returns verified
`graft_principal_id`, `graft_tenant_id`, effective Role attributes,
`graft_initiation_mode`, and audit actor attributes through typed `allow`,
`deny`, or `duplicate` outcomes. Valid webhook replay keys have an atomic
Tenant-scoped duplicate disposition and return the original `graft_run_id`;
raw secrets are excluded from decisions and audit records.

The proposal deliberately leaves provider-specific HMAC canonicalisation and
certificate PKI details to explicit integration/configuration contracts. It
also records the required design companion and mTLS peer, replay-race, typed
identity, Authority Service separation, and audit-redaction evidence. The
Authority Service remains one deployable with logically distinct Token
Service/Authorisation Server, Tool Gateway, and Tool Registry modules.

This is a proposed decision prerequisite for Gate 1 Task 2, not production
implementation or verification evidence. The plan task and all Gate 1/Phase 1
completion claims remain under parent validation and are intentionally
unchanged.

## Gate 1 Task 2 — ADR-0079 owner-selected two-call revision

> **Date:** 2026-09-20

ADR-0079 remains **proposed** and records the explicit owner-selected model:
the first mTLS call sends the raw opaque surface credential to the Token
Service and returns only a typed `allow` or `deny` identity decision. It does
not return a Token-Service-native duplicate/replay disposition, a token, a
`graft_run_id`, or a signed/server-generated resolution handle. The
`graft_run_id` does not exist at that point.

After a first-call `allow`, the Harness API generates the
`graft_harness_replay_key` and owns one atomic webhook replay/idempotency and
Run-creation operation in the Harness Run repository. That operation returns
an existing or new `graft_run_id`. There is no distributed transaction
between Token Service identity/replay state and the Harness Run store.

The second mTLS call receives the raw credential again and the
Harness-created or Harness-returned `graft_run_id`. The Token Service
re-verifies the raw credential, accepts the Run identifier only from the
authenticated first-party Harness API mTLS peer, and mints the run-scoped
capability token without looking up the Harness Run store. Caller-provided
identity is not trusted. The ADR also specifies TLS-handshake failure with no
application response, application-layer typed denial for a valid but
non-allow-listed peer, raw-credential no-leakage requirements, and
second-call credential/Run binding and replay tests.

This revision remains a proposed decision prerequisite for Gate 1 Task 2,
pending owner/parent acceptance and the companion design. It is not
implementation or verification evidence, does not complete Task 2, and does
not change any Gate 1 or Phase 1 completion claim.

The preceding Task 2 entry is retained unchanged because these notes are
append-only; where it describes the earlier one-call/Token-Service duplicate
model, this immediately following owner-selected revision is the current
proposal.

## Gate 1 Task 2 — ADR-0079 clarification finalisation

> **Date:** 2026-09-20

The owner-approved clarifications are now recorded in the proposed ADR and its
living companion. ADR-0079 remains **proposed**; this entry does not accept
the ADR, implement Authority Service identity resolution, or claim Gate 1 or
Phase 1 completion.

The current proposal requires the Harness to persist the first verified
identity binding with an immutable Run/replay record before the mint call.
The second call resubmits the raw surface credential verbatim for every
surface, repeats the canonical normalised webhook envelope when applicable,
and re-verifies credential signature and freshness. Before using the token,
the Harness compares the fresh verified identity, service identity,
initiation mode and webhook fingerprint to that persisted binding. The Token
Service trusts `graft_run_id` only from the authenticated first-party Harness
peer and does not query the Harness Run store; the calls and Run transaction
are not a distributed transaction.

The Harness replay repository taxonomy is exactly `new`, `existing`, or
`conflict`. Equivalent duplicate deliveries return `existing` and the
original Run; the same Tenant and replay key with a changed fingerprint,
verified identity, service identity or initiation mode returns `conflict`,
not a duplicate or generic denial. The webhook fingerprint is the SHA-256 of
deterministic, order-independent canonical JSON over configured semantic
source, event, delivery and alert fields. Transport-only receipt time, raw
provider payload and raw provider secret are excluded. Its canonicalisation
revision and field configuration are versioned in the design/integration
entry and are separate from provider HMAC canonicalisation.

The first resolution is bound to minting by a configured short TTL. Expiry
is a typed denial with no token. This supports immediate Run-start minting
only; delayed tool use and later run-token renewal require a separate design.
mTLS handshake failure has no application response, while a successfully
handshaken but non-allow-listed peer receives a typed denial. All internal
calls are mTLS-only with no fallback. Identity-provider provisioning,
account linking and external-identity mapping are explicitly non-decisions.
More than one Token Service caller invalidates the first-party mTLS trust
assumption and requires a new ADR.

## Gate 1 Task 2 — ADR-0079 formal acceptance

> **Date:** 2026-09-20

The project owner formally accepted [ADR-0079](../../docs/adr/identity/0079-internal-surface-credential-resolution-uses-mtls-and-typed-decisions.md)
on 2026-09-20. This records acceptance of the architectural decision and
design boundary only. It does not claim Authority Service implementation,
verification or release evidence, Task 2 completion, Gate 1 completion, or
Phase 1 completion.

ADR-0079 section 5 remains mandatory follow-on implementation and release
evidence. Its verification matrix is not a precondition to accepting the
architectural decision, but every required guarantee and test remains
outstanding until the implementation and release work produces the specified
evidence. Task 2 implementation/evidence remains pending and parent
validation owns the Gate 1 decision.

## Gate 1 Task 2 — bounded pre-PostgreSQL authority protocol slice

> **Date:** 2026-09-20

Implemented the bounded follow-on slice under accepted [ADR-0079](../../docs/adr/identity/0079-internal-surface-credential-resolution-uses-mtls-and-typed-decisions.md), without changing the existing HTTP API, service, store or security reference modules, ADRs, design/specification/plan files, or migrations. The new `authority/` package contains the strict closed v1 protocol model, canonical normalised webhook fingerprint, configurable deterministic `SurfaceVerifier`, test-only Token Service, redacted test-only audit intent recorder, and standard-library loopback mTLS integration server. `harness/authority_client.py` and `harness/run_initiation.py` implement the first raw-credential allow/deny call, Harness-owned immutable `new`/`existing`/`conflict` replay binding, TTL, fresh second verification comparison, and exact `graft_run_id` capability mint exchange.

The capability issuer is explicitly labelled **test-only opaque token service**. It has no signing key, JWKS, or signing isolation reachable from Harness code and does not claim Task 5. The repository is an in-memory test double only; PostgreSQL durable replay/RLS/audit Tasks 3/4 remain pending. The audit recorder stores redacted intent only and is not durable audit evidence. No Tool Gateway or Tool Registry was added.

Added `contracts/authority-internal-v1.openapi.json` and `scripts/check_authority_contracts.py` for the closed two-call mTLS contract. The tests generate ephemeral certificates in temporary directories and cover valid peer, missing/untrusted/expired TLS failure without an application response, valid TLS wrong-peer typed denial, bearer/plain HTTP rejection, exact whitespace/Unicode credential repeat, no credential leakage in responses or test audit intent, order-independent and semantic webhook fingerprints, replay taxonomy, changed valid identity conflict, TTL expiry, and mint retry without a second Run.

Local bounded validation passed for the new authority/harness tests (11 selected tests), authority contract check, Ruff formatting/linting and lock consistency. The parent validation owner must run the full repository quality suite and must not check Gate 1 Task 2: PostgreSQL durable replay/RLS/audit Tasks 3/4 and production signing/JWKS isolation remain outstanding.
