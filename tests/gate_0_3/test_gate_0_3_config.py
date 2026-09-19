from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.gate_0_3
ROOT = Path(__file__).parents[2]
COMPOSE = ROOT / "deployment/gate-0.3/docker-compose.yml"
RUNNER = ROOT / "deployment/gate-0.3/run_experiment.py"
MATRIX_RUNNER = ROOT / "deployment/gate-0.3/matrix_runner.py"
MATRIX_WORKER = ROOT / "deployment/gate-0.3/matrix_worker.py"
VERSION_PROBE = ROOT / "deployment/gate-0.3/version-probe.py"
RECOVERY_RACE = ROOT / "deployment/gate-0.3/recovery_race.py"


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
    recovery = (ROOT / "deployment/gate-0.3/recovery_race.py").read_text()
    assert "docker" in recovery
    assert "container" in recovery
    assert "winning_executor_is_scenario_b" in recovery
    assert "wrong_revision_reaper_probe" in recovery
    assert "graft_gate03_recovery_reservations_v3" in recovery
    assert "reservation_cas_lost" in recovery
    assert "_recover_pending_workflows" not in recovery
    assert "system-table" in recovery or "system table" in recovery


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


def test_runtime_boundary_and_revision_selection_are_explicit() -> None:
    recovery = RECOVERY_RACE.read_text()
    assert "DBOSClient.resume_workflow" in recovery
    assert "_recover_pending_workflows" not in recovery
    assert "wrong_revision_reaper_probe" in recovery
    assert "application_db_via_transaction_mode_pgbouncer" in recovery


def test_synthetic_effect_service_enforces_run_step_key_contract(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("gate_0_3_recovery_race", RECOVERY_RACE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ledger = module.EffectState(str(tmp_path / "effect-ledger.sqlite3"))
    try:
        run_id = "graft-run-test"
        step_id = module.STEP_ID
        valid = {
            "workflow_id": run_id,
            "graft_run_id": run_id,
            "durable_step_id": step_id,
            "effect_key": module.durable_effect_key(run_id, step_id),
            "executor_id": "executor-test",
        }
        first_call, first_applied = ledger.record_effect(valid)
        second_call, second_applied = ledger.record_effect(valid)
        assert first_call == 1
        assert second_call == 2
        assert first_applied is True
        assert second_applied is False
        summary = ledger.summary()
        assert summary["raw_call_count"] == 2
        assert summary["keyed_effect_count"] == 1

        invalid = {**valid, "effect_key": "not-derived-from-run-and-step"}
        with pytest.raises(ValueError, match="key contract"):
            ledger.record_effect(invalid)
        assert ledger.summary()["contract_violation_count"] == 1
    finally:
        ledger.close()


def test_inventory_requires_b_until_explicit_promotion(tmp_path: Path) -> None:
    inventory = (
        ROOT / "specs/phase-1-walking-skeleton/evidence/gate-0.3/phase-1-effect-inventory.json"
    ).read_text()
    import json

    effects = json.loads(inventory)["effects"]
    assert effects
    assert all(item["classification"] == "B" for item in effects)
    assert all(item["operator_escalation"] is True for item in effects)
    assert all(item["promotion_criteria"]["candidate_classification"] == "A" for item in effects)
