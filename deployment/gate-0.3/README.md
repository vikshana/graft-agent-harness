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

The runner writes redacted evidence under
`specs/phase-1-walking-skeleton/evidence/gate-0.3/`. Runtime `.env` files and
credentials are ignored by the repository. Gate 0 fast CI must use an explicit
marker expression such as `-m "unit or contract"`; `gate_0_3` is never selected
by that expression.
