from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.gate_0_3
ROOT = Path(__file__).parents[2]
COMPOSE = ROOT / "deployment/gate-0.3/docker-compose.yml"
RUNNER = ROOT / "deployment/gate-0.3/run_experiment.py"


def test_gate_0_3_files_are_local_only_and_reproducible() -> None:
    compose = COMPOSE.read_text()
    assert (
        "image: postgres@sha256:f1c3376c26f2609ab9f29f71f824103fe2fcd8ee0346485cb6122a4f93df6f94"
        in compose
    )
    assert compose.count("image: postgres@sha256:") == 2
    assert "image: edoburu/pgbouncer@sha256:" in compose
    assert "4c1ca296ef525f108f5d3552cc337c0c09587cf8dae7f0067fd93349e47dc1cd" in compose
    assert "POOL_MODE: transaction" in compose
    assert "G03_DB_PASSWORD" in compose
    assert "customer_system_access" in RUNNER.read_text()


def test_fast_ci_marker_expression_excludes_gate_0_3() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert '"gate_0_3:' in pyproject
    assert 'pytest -m "unit or contract"' in (ROOT / "README.md").read_text()


def test_no_runtime_secret_or_evidence_files_are_checked_in() -> None:
    assert ".env" in (ROOT / ".gitignore").read_text()
    evidence = ROOT / "specs/phase-1-walking-skeleton/evidence/gate-0.3"
    if evidence.exists():
        for path in evidence.iterdir():
            assert path.name == "README.md" or path.suffix in {".json", ".txt", ".log"}
            assert "gate03_local_only" not in path.read_text()
