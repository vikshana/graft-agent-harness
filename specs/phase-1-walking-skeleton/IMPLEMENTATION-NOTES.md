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


## Gate 0.3 experiment evidence

> **Date:** 2026-09-18

Added the bounded throwaway harness under `deployment/gate-0.3/`, with pinned
local PostgreSQL 16 and PgBouncer image digests, separate application/system
databases, transaction pooling, ignored synthetic runtime environment
creation, and redacted evidence output. The `gate_0_3` pytest marker is
registered separately; fast CI continues to select only `unit or contract`.

The Docker experiment ran successfully on Docker 29.5.2 / Compose
v2.40.3-desktop.1 using DBOS 3.0.0, Python 3.12.6, and the locked dependency
graph. Application and transaction-mode pooler database probes connected. The
redacted evidence files are `result.json` and `commands.json` under
`specs/phase-1-walking-skeleton/evidence/gate-0.3/`.

| Question | Actual result |
|----------|---------------|
| G03-A | Compatibility was corrected to `langchain-mcp-adapters==0.3.2` with `mcp==1.28.1`. The real synthetic streamable-HTTP MCP server/client invocation passed inside the DBOS workflow; the no-checkpointer LangGraph graph, decorated graph/MCP/failure-injection steps, and MCP failure capture also passed. |
| G03-B | Alive-but-silent recovery remains unresolved through public APIs. Timeout is not treated as proof. The isolated synthetic idempotency exercise repeated one workflow ID/input and is not recovery proof. |
| G03-C | Conductor-free `list_workflows(executor_id=...)` filtering passed: one matching workflow for `gate03-executor-a`, zero for the synthetic non-matching executor. |
| G03-D | Identical-source application-version recomputation was stable; an in-process source-change registration produced a different recomputed hash. A second-process/reloaded-source deployment check remains required before claiming full source-change runtime behaviour. |

Gate 0.3 remains unchecked. The raw local `.env` and containers were removed
after the run; no credentials were written to evidence. Parent validation owns
interpretation of this partial evidence and the remaining blockers.

## Proposed ADR dispositions from Gate 0.3

> **Date:** 2026-09-18

Drafted proposed [ADR-0076](../../docs/adr/agent/0076-recovery-requires-confirmed-termination-or-an-independent-fence.md)
to amend ADR-0038. The Gate 0.3 G03-B evidence does not prove safe ownership
fencing for an alive-but-silent executor, so stale heartbeat or timeout alone is
not a safe recovery trigger. The proposal requires confirmed termination or an
independently proven fence/lease compare-and-set before re-enqueueing, while
leaving the production mechanism undecided pending crash, partition and
concurrent-reaper tests.

Drafted proposed [ADR-0077](../../docs/adr/agent/0077-auto-versioning-must-account-for-dependency-upgrades.md)
to amend ADR-0046. Gate 0.3 records DBOS 3 auto-version stability for identical
source/runtime and a changed source hash; DBOS 3 also includes its package
version in the computed hash. The proposal accepts dependency-upgrade drains as
the conservative disposition, preserves version-compatible recovery, and keeps
Git/image version pinning rejected. A controlled alternative requires an
independent compatibility and rollback proof.

Both ADRs are proposed only; no accepted ADR was edited and no plan checkbox
was changed. Parent validation and project-owner approval remain required.
