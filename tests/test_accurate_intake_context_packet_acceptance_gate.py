from __future__ import annotations

import json
from pathlib import Path

from app.composition import accurate_intake_context_packet_acceptance_gate as module
from app.composition.accurate_intake_context_packet_acceptance_gate import (
    build_context_packet_acceptance_gate_artifact,
)


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(scenario["scenario_id"]): scenario
        for scenario in artifact["scenarios"]  # type: ignore[index]
    }


def test_context_packet_acceptance_gate_proves_context_changes_runtime_routing() -> None:
    artifact = build_context_packet_acceptance_gate_artifact()

    assert artifact["artifact_type"] == "accurate_intake_context_packet_acceptance_gate"
    assert artifact["status"] == "pass"
    assert artifact["runtime_backed"] is True
    assert artifact["live_llm_invoked"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["deterministic_selected_intent"] is False
    assert artifact["deterministic_selected_target"] is False

    by_id = _by_id(artifact)
    no_context = by_id["half_sugar_no_context"]
    resolved_target = by_id["half_sugar_resolved_target"]
    pending_followup = by_id["pending_followup_answer"]
    ui_target = by_id["ui_explicit_target_action"]

    assert no_context["raw_user_input"] == resolved_target["raw_user_input"] == "改半糖"
    assert no_context["target_workflow_family"] == "general_chat"
    assert no_context["disposition"] == "defer"
    assert no_context["candidate_attachment_target_count"] == 0
    assert no_context["open_workflow_type"] == "none"

    assert resolved_target["target_workflow_family"] == "intake"
    assert resolved_target["disposition"] == "correct"
    assert resolved_target["attachment_reason"] == "resolved_target_reference"
    assert resolved_target["candidate_attachment_target_count"] == 1
    assert resolved_target["open_workflow_type"] == "meal_correction"

    assert pending_followup["target_workflow_family"] == "intake"
    assert pending_followup["disposition"] == "continue"
    assert pending_followup["attachment_reason"] == "pending_followup_answer"
    assert pending_followup["open_workflow_type"] == "meal_followup"

    assert ui_target["target_workflow_family"] == "intake"
    assert ui_target["disposition"] == "continue"
    assert ui_target["attachment_reason"] == "explicit_interaction_target"
    assert ui_target["interaction_source"] == "ui"


def test_context_packet_acceptance_gate_preserves_read_only_context_support_surfaces() -> None:
    artifact = build_context_packet_acceptance_gate_artifact()
    by_id = _by_id(artifact)

    pending_followup = by_id["pending_followup_answer"]
    resolved_target = by_id["half_sugar_resolved_target"]

    assert pending_followup["phase_a_trace_present"] is True
    assert pending_followup["pending_followup_present"] is True
    assert pending_followup["current_budget_snapshot_present"] is True
    assert pending_followup["target_resolution_posture_read_only"] is True
    assert pending_followup["candidate_attachment_targets_read_only"] is True
    assert pending_followup["manager_context_pack_present"] is True
    assert pending_followup["manager_context_current_budget_snapshot_read_only"] is True
    assert "followup_or_correction_context" in pending_followup["promotion_reasons"]
    assert pending_followup["manager_context_promoted_target_resolution_posture"] is True
    assert pending_followup["manager_context_promoted_recent_item_targets"] is True

    assert resolved_target["phase_a_trace_present"] is True
    assert resolved_target["target_resolution_source"] == "manager_structured_target"
    assert resolved_target["target_resolution_posture_read_only"] is True
    assert resolved_target["candidate_attachment_targets_read_only"] is True
    assert resolved_target["manager_context_pack_present"] is True
    assert resolved_target["manager_context_current_budget_snapshot_read_only"] is True
    assert "followup_or_correction_context" in resolved_target["promotion_reasons"]
    assert resolved_target["manager_context_promoted_target_resolution_posture"] is True
    assert resolved_target["manager_context_promoted_recent_item_targets"] is True


def test_context_packet_acceptance_gate_cli_writes_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "context_packet_acceptance_gate.json"

    from scripts.run_accurate_intake_context_packet_acceptance_gate import main

    exit_code = main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["summary"]["scenario_count"] == 4


def test_context_packet_acceptance_gate_materializes_fresh_fixture_state_per_run() -> None:
    scenarios = module._scenarios()
    scenarios[0]["promotion_reasons"].append("mutated")

    fresh = build_context_packet_acceptance_gate_artifact()
    no_context = _by_id(fresh)["half_sugar_no_context"]

    assert "mutated" not in no_context["promotion_reasons"]
