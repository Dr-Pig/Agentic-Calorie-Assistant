from __future__ import annotations

import json
from pathlib import Path

from scripts.run_accurate_intake_rt6_bootstrap_no_plan_body_closure import (
    build_rt6_bootstrap_no_plan_body_closure_artifact,
    main,
)


def test_rt6_bootstrap_no_plan_body_closure_artifact_passes_all_cases() -> None:
    artifact = build_rt6_bootstrap_no_plan_body_closure_artifact()

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt6_bootstrap_no_plan_body_closure"
    assert artifact["supports_journeys"] == ["A", "G", "H", "J"]
    assert artifact["summary"] == {"case_count": 4, "passed_case_count": 4}
    case_by_id = {case["case_id"]: case for case in artifact["cases"]}
    assert case_by_id["bootstrap_ready"]["status"] == "pass"
    assert case_by_id["no_plan_honesty"]["answer_status"] == "onboarding_required"
    assert case_by_id["manager_body_observation_write"]["latest_weight_value"] == 70.0
    assert case_by_id["weight_route_write"]["latest_weight_value"] == 69.5
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False


def test_rt6_bootstrap_no_plan_body_closure_cli_writes_artifact(tmp_path: Path) -> None:
    output = tmp_path / "rt6_bootstrap_no_plan_body_closure.json"

    exit_code = main(["--output", str(output)])

    assert exit_code == 0
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["gate_id"] == "accurate_intake_rt6_bootstrap_no_plan_body_closure"
    assert artifact["status"] == "pass"
    assert artifact["artifact_name"] == "rt6_bootstrap_no_plan_body_closure.json"
    assert artifact["fixture_or_real"] == "fixture"
    assert artifact["producer_track"] == "CurrentShell/ManagerRuntime"
    assert artifact["ready_for_other_tracks"] is True
    assert artifact["non_claims"]["real_fooddb_pass_claimed"] is False
