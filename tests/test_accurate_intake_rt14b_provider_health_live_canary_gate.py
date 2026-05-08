from __future__ import annotations

import importlib
import json
from pathlib import Path

from scripts.build_accurate_intake_rt14b_provider_health_live_canary_gate import (
    build_rt14b_provider_health_live_canary_gate,
)


def _build_live_provider_health_report(tmp_path: Path) -> dict:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")
    return module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic_provider_health.json",
        db_path=tmp_path / "accurate_intake_mvp_live_diagnostic_provider_health.sqlite3",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="live",
        live_invoked=True,
        stage="provider_health_smoke",
    )


def test_rt14b_provider_health_live_canary_gate_passes_for_strict_live_probe(tmp_path: Path) -> None:
    source = _build_live_provider_health_report(tmp_path)

    artifact = build_rt14b_provider_health_live_canary_gate(
        live_diagnostic_artifact=source,
    )

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt14b_provider_health_live_canary"
    assert artifact["pass_type"] == "live_diagnostic"
    assert artifact["summary"]["required_stage_id"] == "provider_health_smoke"
    assert artifact["summary"]["required_result_kind"] == "strict_pass_first_attempt"
    assert artifact["summary"]["non_claim_flags_preserved"] is True


def test_rt14b_provider_health_live_canary_gate_blocks_non_live_artifact(tmp_path: Path) -> None:
    source = _build_live_provider_health_report(tmp_path)
    source["provider_mode"] = "fake_provider_contract_test"
    source["live_invoked"] = False

    artifact = build_rt14b_provider_health_live_canary_gate(
        live_diagnostic_artifact=source,
    )

    assert artifact["status"] == "fail"
    assert "provider_mode_not_live" in artifact["blockers"]
    assert "live_not_invoked" in artifact["blockers"]


def test_rt14b_provider_health_live_canary_gate_blocks_retry_dependent_pass(tmp_path: Path) -> None:
    source = _build_live_provider_health_report(tmp_path)
    source["stages"][0]["result_kind"] = "pass_after_retry"
    source["stages"][0]["retry_policy_applied"] = True

    artifact = build_rt14b_provider_health_live_canary_gate(
        live_diagnostic_artifact=source,
    )

    assert artifact["status"] == "fail"
    assert "stage_not_strict_first_attempt:provider_health_smoke" in artifact["blockers"]


def test_rt14b_provider_health_live_canary_gate_cli_writes_json(tmp_path: Path) -> None:
    source = _build_live_provider_health_report(tmp_path)
    source_path = tmp_path / "source.json"
    source_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "accurate_intake_rt14b_provider_health_live_canary_gate.json"

    from scripts.build_accurate_intake_rt14b_provider_health_live_canary_gate import main

    exit_code = main(
        [
            "--source-artifact",
            str(source_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "accurate_intake_rt14b_provider_health_live_canary_gate"
    assert payload["status"] == "pass"
