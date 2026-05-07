from __future__ import annotations

import importlib
import json
from pathlib import Path


def test_rt8_overshoot_runtime_truth_artifact(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_rt8_overshoot_runtime_truth")
    output_path = tmp_path / "accurate_intake_rt8_overshoot_runtime_truth.json"

    artifact = module.build_rt8_overshoot_runtime_truth_artifact(output_path=output_path)

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt8_overshoot_runtime_truth"
    assert artifact["supports_journeys"] == ["E"]
    assert artifact["runtime_backed"] is True
    assert artifact["live_llm_invoked"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["summary"]["case_count"] == 3
    assert artifact["summary"]["passed_case_count"] == 3
    assert {case["case_id"] for case in artifact["cases"]} == {
        "overshoot_reflects_budget_truth_without_rescue_context",
        "correction_restores_under_target_runtime_truth",
        "budget_answer_and_debug_model_share_overshoot_truth",
    }
    assert output_path.exists() is False


def test_rt8_main_writes_artifact(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_rt8_overshoot_runtime_truth")
    output_path = tmp_path / "accurate_intake_rt8_overshoot_runtime_truth.json"

    exit_code = module.main(["--output", str(output_path)])

    assert exit_code == 0
    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["status"] == "pass"
    assert written["artifact_name"] == output_path.name
