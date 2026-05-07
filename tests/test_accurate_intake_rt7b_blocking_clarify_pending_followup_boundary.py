from __future__ import annotations

import importlib
import json
from pathlib import Path


def test_rt7b_blocking_clarify_pending_followup_boundary_artifact(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_rt7b_blocking_clarify_pending_followup_boundary")
    output_path = tmp_path / "accurate_intake_rt7b_blocking_clarify_pending_followup_boundary.json"

    artifact = module.build_rt7b_blocking_clarify_pending_followup_boundary_artifact(output_path=output_path)

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt7b_blocking_clarify_pending_followup_boundary"
    assert artifact["supports_journeys"] == ["D"]
    assert artifact["runtime_backed"] is True
    assert artifact["live_llm_invoked"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["summary"] == {"case_count": 3, "passed_case_count": 3}
    assert {case["case_id"] for case in artifact["cases"]} == {
        "blocking_clarify_route_no_commit",
        "pending_followup_persisted",
        "next_turn_context_packet_pending_followup",
    }

    assert output_path.exists() is False


def test_rt7b_main_writes_artifact(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_rt7b_blocking_clarify_pending_followup_boundary")
    output_path = tmp_path / "accurate_intake_rt7b_blocking_clarify_pending_followup_boundary.json"

    exit_code = module.main(["--output", str(output_path)])

    assert exit_code == 0
    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["status"] == "pass"
    assert written["artifact_name"] == output_path.name
