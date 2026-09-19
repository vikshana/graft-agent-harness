# Graft Agent Harness

This repository contains the Phase 1 API-first walking skeleton. The checked-in
prototype is intentionally small and keeps production DBOS, PostgreSQL,
streamable-HTTP MCP, OTel, and Grafana transports behind explicit seams. The
package metadata now defines the production Python and dependency baseline;
the prototype remains reference code until the later persistence, durability,
authority, and observability gates are complete.

## Supported baseline

- Python 3.11, 3.12, and 3.13.
- Runtime dependencies are locked in `uv.lock` and constrained in
  `pyproject.toml`.
- The immediate DBOS experiment also has the runtime constraint
  `langchain-mcp-adapters`.
- The development group contains Ruff, mypy, pytest, pip-audit, and
  pip-licenses.

## Bootstrap

Install [uv](https://docs.astral.sh/uv/) and create the locked development
environment:

```sh
uv sync --locked --all-groups
```

The command creates `.venv` and installs both runtime and development
dependencies from `uv.lock`. Use `uv run ...` for all commands below so that
the lock-selected environment is used.

## Local verification

```sh
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest -m "unit or contract"
uv run python scripts/check_step_pointer_rule.py harness
uv run python scripts/check_architecture.py harness
uv run python scripts/check_docs.py
uv export --locked --no-dev --no-emit-project --format requirements-txt \
  --output-file /tmp/graft-locked-requirements.txt
uv run pip-audit --strict --requirement /tmp/graft-locked-requirements.txt
uv run pip-licenses --format=markdown --with-urls
```

The licence command is an evidence inventory only. The project owner has
approved retaining this inventory control; no licence allow/deny policy is
defined.

The canonical Collector configuration referenced by
`docs/design/observability-pipeline.md` is present at
`deployment/otel-collector/config.yaml`. Local verification with
`uv run python scripts/check_docs.py` passed with 0 errors and 0 warnings.

The authoritative semantic contract is `contracts/harness-v1.openapi.json`; the event schema is `contracts/run-events-v1.schema.json`. The reference PostgreSQL migration is `migrations/001_phase1.sql`.
