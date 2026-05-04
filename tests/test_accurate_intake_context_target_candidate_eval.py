from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_context_target_candidate_eval import (
    build_context_target_candidate_eval_artifact,
)


def test_context_target_candidate_eval_uses_fixture_manager_decisions_without_selecting_targets() -> None:
    artifact = build_context_target_candidate_eval_artifact()

    assert artifact["artifact_type"] == "accurate_intake_context_target_candidate_eval"
    assert artifact["status"] == "generated"
    assert artifact["diagnostic_only"] is True
    assert artifact["fixture_manager_used"] is True
    assert artifact["deterministic_semantic_inference_used"] is False
    assert artifact["deterministic_selected_target"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["mutation_authority"] is False
    assert artifact["fooddb_truth_updated"] is False

    assert [scenario["scenario_id"] for scenario in artifact["scenarios"]] == [
        "remove_previous_reference",
        "remove_named_item",
        "modify_drink_sugar",
        "modify_rice_portion",
        "correct_previous_identity",
    ]
    assert all(
        scenario["semantic_source"] == "fixture_manager_structured_decision"
        for scenario in artifact["scenarios"]
    )
    assert all(
        scenario["raw_user_input_role"] == "display_only"
        for scenario in artifact["scenarios"]
    )
    assert all(
        scenario["context_target_candidates_present"] is True
        for scenario in artifact["scenarios"]
    )
    assert artifact["summary"]["ambiguous_scenarios"] >= 2


def test_context_target_candidate_eval_marks_ambiguity_as_manager_or_clarification_work() -> None:
    artifact = build_context_target_candidate_eval_artifact()
    by_id = {scenario["scenario_id"]: scenario for scenario in artifact["scenarios"]}

    assert by_id["remove_previous_reference"]["target_resolution_status"] == "ambiguous"
    assert by_id["remove_previous_reference"]["requires_manager_or_clarification"] is True
    assert by_id["modify_drink_sugar"]["target_resolution_status"] == "candidate_supported"
    assert by_id["modify_drink_sugar"]["deterministic_selected_target"] is False
    assert by_id["correct_previous_identity"]["requires_manager_or_clarification"] is True


def test_context_target_candidate_eval_builder_script_writes_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "target_eval.json"

    from scripts.run_accurate_intake_context_target_candidate_eval import main

    exit_code = main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["scenario_count"] == 5
    assert artifact["real_fooddb_pass_claimed"] is False
