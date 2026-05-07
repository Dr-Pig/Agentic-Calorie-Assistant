from __future__ import annotations

import json
from pathlib import Path

from scripts.run_accurate_intake_rt7a_correction_removal_runtime_boundary import (
    build_rt7a_correction_removal_runtime_boundary_artifact,
    main,
)


def test_rt7a_correction_removal_runtime_boundary_artifact_passes_all_cases() -> None:
    artifact = build_rt7a_correction_removal_runtime_boundary_artifact()

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt7a_correction_removal_runtime_boundary"
    assert artifact["supports_journeys"] == ["K"]
    assert artifact["summary"] == {"case_count": 5, "passed_case_count": 5}
    case_by_id = {case["case_id"]: case for case in artifact["cases"]}
    assert case_by_id["single_item_reference"]["status"] == "pass"
    assert case_by_id["ambiguous_multi_item_reference"]["status"] == "pass"
    assert case_by_id["item_level_correction"]["status"] == "pass"
    assert case_by_id["explicit_item_removal"]["status"] == "pass"
    assert case_by_id["remove_target_evidence_boundary"]["status"] == "pass"


def test_rt7a_correction_removal_runtime_boundary_cli_writes_artifact(tmp_path: Path) -> None:
    output = tmp_path / "rt7a_correction_removal_runtime_boundary.json"

    exit_code = main(["--output", str(output)])

    assert exit_code == 0
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["artifact_name"] == "rt7a_correction_removal_runtime_boundary.json"
    assert artifact["fixture_or_real"] == "real_runtime_local"
    assert artifact["producer_track"] == "CurrentShell/ManagerRuntime"
    assert artifact["ready_for_other_tracks"] is True
    assert artifact["non_claims"]["real_fooddb_pass_claimed"] is False
