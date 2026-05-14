from __future__ import annotations

import importlib
import json
from pathlib import Path


def test_rt7c_single_turn_commit_boundary_artifact(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_rt7c_single_turn_commit_boundary")
    output_path = tmp_path / "accurate_intake_rt7c_single_turn_commit_boundary.json"
    db_path = tmp_path / "accurate_intake_rt7c_single_turn_commit_boundary.sqlite3"

    artifact = module.build_rt7c_single_turn_commit_boundary_artifact(
        output_path=output_path,
        db_path=db_path,
    )

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt7c_single_turn_commit_boundary"
    assert artifact["supports_journeys"] == ["B"]
    assert artifact["runtime_backed"] is True
    assert artifact["live_llm_invoked"] is False
    assert artifact["summary"] == {"case_count": 1, "passed_case_count": 1}
    case = artifact["case"]
    assert case["case_id"] == "single_turn_commit_boundary"
    assert case["status"] == "pass"
    assert case["manager_pass_count"] == 2
    assert "estimate_nutrition" in case["requested_tools"]
    assert "estimate_nutrition" in case["executed_tools"]
    assert set(case["requested_tools"]).issubset({"estimate_nutrition", "compare_against_budget"})
    assert set(case["executed_tools"]).issubset({"estimate_nutrition", "compare_against_budget"})
    assert case["transition_guard_verdict"] == "pass"
    assert case["canonical_commit_status"] == "committed"
    assert case["same_truth_status"] == "pass"
    assert output_path.exists() is False


def test_rt7c_main_writes_artifact(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_rt7c_single_turn_commit_boundary")
    output_path = tmp_path / "accurate_intake_rt7c_single_turn_commit_boundary.json"
    db_path = tmp_path / "accurate_intake_rt7c_single_turn_commit_boundary.sqlite3"

    exit_code = module.main(["--output", str(output_path), "--db-path", str(db_path)])

    assert exit_code == 0
    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["status"] == "pass"
    assert written["artifact_name"] == output_path.name
