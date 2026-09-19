# Implementation Notes: Phase 1 API-first walking skeleton

> **Date:** 2026-09-17

---

## Summary

Added a runnable, dependency-light API contract/provider core for the Phase 1 walking skeleton. It models private read-only Runs, ordered replayable events, idempotent webhook creation, cancellation boundaries, capability-token validation, curated Tool Gateway calls, and a WSGI HTTP adapter while leaving production DBOS, PostgreSQL, MCP, telemetry, and surface transport integrations behind explicit seams.

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
now records the owner-selected proposal to supersede ADR-0046: every mutually
versioned release receives an explicit released application compatibility
revision, every prior release cohort drains, and the value is not a mutable Git
SHA or image tag. The Gate 0.3 version matrix found a false-compatible
helper-only change and a direct DBOS-version change, but did not exercise
operational draining, orphan alerts, matching-version recovery, or reverse-drain
rollback. ADR-0077 remains proposed pending formal owner acceptance.

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
Gate 0.3 closure evidence. The following required tests remain outstanding:

| Required evidence | Current status |
|---|---|
| Recovery barrier/partition matrix: before effect, after effect before checkpoint, and after the final step before outcome write, including the system-database network cut | Outstanding |
| Both-handle outcomes plus concurrent resume and crash cases | Outstanding |
| Phase 1 external-effect inventory, with receiving-boundary idempotency tests and an explicit operator-escalation classification for every non-idempotent effect | Outstanding |

Gate 0.3 remains unresolved and Gate 1 remains blocked. ADR-0077 remains
proposed pending formal owner acceptance and operational evidence for the
all-release drain, including `PENDING`, `ENQUEUED`, and `DELAYED` drain checks,
orphan alerts, matching-version recovery, and reverse-drain rollback.

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
value is not a mutable Git SHA or image tag. ADR-0077 remains proposed pending
formal owner acceptance and operational drain evidence; Gate 0.3 remains
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
