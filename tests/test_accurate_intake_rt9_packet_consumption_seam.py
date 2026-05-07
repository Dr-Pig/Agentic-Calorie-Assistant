from __future__ import annotations

import importlib
import json
from pathlib import Path


def test_rt9_packet_consumption_seam_artifact(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_rt9_packet_consumption_seam")
    output_path = tmp_path / "accurate_intake_rt9_packet_consumption_seam.json"

    artifact = module.build_rt9_packet_consumption_seam_artifact(output_path=output_path)

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt9_packet_consumption_seam"
    assert artifact["supports_journeys"] == ["B"]
    assert artifact["runtime_backed"] is True
    assert artifact["live_llm_invoked"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["summary"] == {"case_count": 3, "passed_case_count": 3}
    assert {case["case_id"] for case in artifact["cases"]} == {
        "manager_owned_exact_brand_packet_reaches_runtime_trace",
        "raw_text_hint_cannot_activate_runtime_web_packet",
        "rejected_web_candidate_never_becomes_evidence_truth",
    }
    assert output_path.exists() is False


def test_rt9_packet_consumption_seam_main_writes_artifact(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_rt9_packet_consumption_seam")
    output_path = tmp_path / "accurate_intake_rt9_packet_consumption_seam.json"

    exit_code = module.main(["--output", str(output_path)])

    assert exit_code == 0
    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["status"] == "pass"
    assert written["artifact_name"] == output_path.name
