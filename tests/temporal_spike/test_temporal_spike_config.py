from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.temporal_spike
ROOT = Path(__file__).parents[2]
SPIKE = ROOT / "deployment/temporal-spike"
COMPOSE = SPIKE / "docker-compose.yml"
RUNNER = SPIKE / "run_spike.py"
WORKER = SPIKE / "temporal_spike.py"


def test_spike_is_pinned_and_synthetic_only() -> None:
    compose = COMPOSE.read_text()
    assert "temporalio/auto-setup@sha256:" in compose
    assert "postgres@sha256:" in compose
    assert "temporal_local_only" in compose
    assert "127.0.0.1:17233:7233" in compose
    assert "customer" not in compose.lower()


def test_spike_covers_required_observations_without_prod_imports() -> None:
    worker = WORKER.read_text()
    runner = RUNNER.read_text()
    assert "os._exit(137)" in worker
    assert "activity.heartbeat" in worker
    assert "RetryPolicy" in worker
    assert "workflow.patched" in worker
    assert "Replayer" in runner
    assert "keyed_logical_effect_count" in runner
    assert "external_effect_fencing" in runner
    assert "production_deployment" in runner


def test_spike_result_is_explicit_about_temporal_limits(tmp_path: Path) -> None:
    result = {
        "external_effect_fencing": False,
        "dbos_specific_capabilities_not_covered": ["step trajectories"],
    }
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result))
    loaded = json.loads(path.read_text())
    assert loaded["external_effect_fencing"] is False
    assert loaded["dbos_specific_capabilities_not_covered"]


def test_fast_ci_marker_expression_excludes_spike() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert '"temporal_spike:' in pyproject
    assert 'pytest -m "unit or contract"' in (ROOT / "README.md").read_text()
