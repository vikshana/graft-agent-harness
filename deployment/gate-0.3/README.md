# Gate 0.3 DBOS experiment

This is a throwaway local experiment only. It starts two PostgreSQL 16
containers and a transaction-mode PgBouncer container. It has no customer-system
access and uses synthetic local credentials only.

```sh
uv run python deployment/gate-0.3/run_experiment.py prepare
docker compose --env-file deployment/gate-0.3/.env -f deployment/gate-0.3/docker-compose.yml up -d
uv run python deployment/gate-0.3/run_experiment.py run
docker compose --env-file deployment/gate-0.3/.env -f deployment/gate-0.3/docker-compose.yml down -v
```

Tests 2 and 3 use the same split-database topology, but deliberately run cohort
workers and version probes as separate processes. Test 2 is explicitly
`REDUCED_FIDELITY`: the public Python API has no expected-executor/version
conditional recovery operation, and its orphan detector is synthetic. The
runner does not use DBOS private recovery functions. Start the containers first,
then run either test or both:

```sh
uv run python deployment/gate-0.3/matrix_runner.py 2
uv run python deployment/gate-0.3/matrix_runner.py 3
uv run python deployment/gate-0.3/matrix_runner.py all
```

Test 2 creates `ENQUEUED`, `DELAYED`, and `PENDING` rows in an old-version
cohort, starts a new-version cohort, kills the old process, observes the rows
through `DBOSClient.list_workflows`, records synthetic orphan candidates, then
uses the public `DBOSClient.resume_workflows` operation only for the same-version
replacement drain. It repeats the same procedure in reverse for rollback. The
evidence does not claim that the new cohort cannot recover old work, because
the public API cannot express that condition safely.

The recovery-barrier lane is run explicitly with:

```sh
uv run python deployment/gate-0.3/run_experiment.py prepare
docker compose --env-file deployment/gate-0.3/.env -f deployment/gate-0.3/docker-compose.yml up -d --wait
uv run python deployment/gate-0.3/recovery_race.py run
docker compose --env-file deployment/gate-0.3/.env -f deployment/gate-0.3/docker-compose.yml down -v
```

It exercises SIGSTOP barriers before the synthetic effect, after the effect
before the step checkpoint, and after the last step before the workflow
outcome. Executor A, executor B and each reaper are disposable containers with
run-unique executor IDs. The system-database partition disconnects only
executor A from the `gate03-system` Docker network; executor B and reapers
retain DBOS access. The lane also runs two concurrent public resume attempts
and kills a reaper after resume acceptance but before terminal recovery, then
retries it. The receiver records both raw calls and keyed applications and
asserts the `graft_run_id:durable_step_id` contract.

Test 3 records DBOS's hash implementation path and digest, source/path
determinism, comments, formatting, step changes, helper-only changes, app-name
changes, locked Python variants, dependency variants, and two independent
container builds. A blocked or unavailable variant remains blocked in the JSON
evidence rather than being inferred. The helper-only unchanged version is
labelled a false-compatible result, not compatible behaviour. Test 3 remains
`REDUCED_FIDELITY`.

The runner writes redacted evidence under
`specs/phase-1-walking-skeleton/evidence/gate-0.3/`. Runtime `.env` files and
credentials are ignored by the repository. Gate 0 fast CI must use an explicit
marker expression such as `-m "unit or contract"`; `gate_0_3` is never selected
by that expression.
