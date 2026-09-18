# Graft Agent Harness

This repository contains the Phase 1 API-first walking skeleton. The first runnable slice is intentionally dependency-light and keeps production DBOS, PostgreSQL, streamable-HTTP MCP, OTel, and Grafana transports behind seams.

## Local verification

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_step_pointer_rule.py harness
python3 scripts/check_docs.py
```

`check_docs.py` currently reports a pre-existing dead link in `docs/design/observability-pipeline.md`; it is unrelated to the harness package.

The authoritative semantic contract is `contracts/harness-v1.openapi.json`; the event schema is `contracts/run-events-v1.schema.json`. The reference PostgreSQL migration is `migrations/001_phase1.sql`.

