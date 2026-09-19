from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.gate_0_3
ROOT = Path(__file__).parents[2]
COMPOSE = ROOT / "deployment/gate-0.3/docker-compose.yml"
RUNNER = ROOT / "deployment/gate-0.3/run_experiment.py"
MATRIX_RUNNER = ROOT / "deployment/gate-0.3/matrix_runner.py"
MATRIX_WORKER = ROOT / "deployment/gate-0.3/matrix_worker.py"
VERSION_PROBE = ROOT / "deployment/gate-0.3/version-probe.py"


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


def test_tests_2_and_3_matrix_is_public_api_only_and_redaction_is_preserved() -> None:
    assert MATRIX_RUNNER.exists()
    assert MATRIX_WORKER.exists()
    assert VERSION_PROBE.exists()
    worker = MATRIX_WORKER.read_text()
    runner = MATRIX_RUNNER.read_text()
    assert "DBOSClient.list_workflows" in worker
    assert "DBOSClient.resume_workflows" in worker
    assert "_recover_pending_workflows" not in worker
    assert "REDUCED_FIDELITY" in runner
    assert "helper_only_change_is_false_compatible" in runner
    assert "gate03_local_only" not in MATRIX_RUNNER.read_text()
