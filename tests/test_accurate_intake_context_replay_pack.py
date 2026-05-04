from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_context_replay_pack import (
    build_context_replay_pack_artifact,
)


def test_context_replay_pack_covers_sensitive_turns_without_deterministic_semantics() -> None:
    artifact = build_context_replay_pack_artifact()

    assert artifact["artifact_type"] == "accurate_intake_context_replay_pack"
    assert artifact["status"] == "generated"
    assert artifact["diagnostic_only"] is True
    assert artifact["deterministic_supplies_candidates_and_pins_only"] is True
    assert artifact["deterministic_semantic_inference_used"] is False
    assert artifact["raw_text_intent_router_used"] is False
    assert artifact["mutation_authority"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert [scenario["scenario_id"] for scenario in artifact["scenarios"]] == [
        "remove_previous_item",
        "remove_named_item",
        "modify_drink_sugar",
        "modify_rice_portion",
        "correct_previous_identity",
        "pending_followup_answer",
        "long_chat_with_pinned_pending_draft",
        "remove_lunch_rice_scoped",
        "modify_previous_drink_unsweetened",
        "pending_quantity_answer",
        "cancel_logging_intent_requires_manager",
        "outside_current_day_reference_omitted",
    ]
    assert all(
        scenario["raw_user_input_role"] == "display_only"
        for scenario in artifact["scenarios"]
    )
    assert artifact["summary"]["ambiguous_scenarios"] >= 2
    assert artifact["summary"]["pending_pin_scenarios"] == 3
    assert artifact["summary"]["manager_semantic_required_scenarios"] == 1
    assert artifact["summary"]["outside_current_day_omitted_scenarios"] == 1
    cancel = {scenario["scenario_id"]: scenario for scenario in artifact["scenarios"]}[
        "cancel_logging_intent_requires_manager"
    ]
    assert cancel["context_candidates_present"] is False
    assert cancel["target_resolution_status"] == "manager_semantic_required"
    outside_day = {scenario["scenario_id"]: scenario for scenario in artifact["scenarios"]}[
        "outside_current_day_reference_omitted"
    ]
    assert outside_day["context_candidates_present"] is False
    assert outside_day["omitted_context_expected"] is True


def test_context_replay_pack_script_writes_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "context_replay.json"

    from scripts.run_accurate_intake_context_replay_pack import main

    exit_code = main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["scenario_count"] == 12
    assert artifact["real_fooddb_pass_claimed"] is False
