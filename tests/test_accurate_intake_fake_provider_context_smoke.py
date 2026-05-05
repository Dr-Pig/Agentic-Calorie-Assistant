from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_fake_provider_context_smoke import (
    build_fake_provider_context_smoke_artifact,
)


def test_fake_provider_context_smoke_reuses_live_shape_without_live_provider() -> None:
    artifact = build_fake_provider_context_smoke_artifact()

    assert artifact["artifact_type"] == "accurate_intake_fake_provider_context_smoke"
    assert artifact["claim_scope"] == "fake_provider_context_smoke"
    assert artifact["status"] == "pass"
    assert artifact["provider_mode"] == "fake_provider_contract_test"
    assert artifact["live_provider_called"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["final_semantic_decision_source"] == "fixture_manager_structured_decision"
    assert artifact["deterministic_semantic_inference_used"] is False
    assert artifact["raw_text_intent_router_used"] is False
    assert artifact["tool_loop_trace_attributable"] is True
    assert artifact["manager_handoff_matrix_checked"] is True
    assert artifact["summary"]["manager_handoff_scenario_count"] >= 6
    assert artifact["summary"]["ambiguous_back_reference_scenarios"] >= 1
    assert artifact["summary"]["query_no_mutation_scenarios"] >= 1
    assert artifact["summary"]["target_update_boundary_scenarios"] >= 2

    provider_input = artifact["provider_input_summary"]
    assert provider_input["context_policy_version_present"] is True
    assert provider_input["loaded_context_summary_present"] is True
    assert provider_input["omitted_context_summary_present"] is True
    assert provider_input["target_candidates_present"] is True
    assert provider_input["forbidden_context_excluded"] is True
    assert provider_input["manager_context_packet_schema_changed"] is False

    by_id = {scenario["scenario_id"]: scenario for scenario in artifact["manager_handoff_scenarios"]}
    ambiguous = by_id["ambiguous_back_reference"]
    assert ambiguous["pre_attachment_disposition"] == "answer_only"
    assert ambiguous["pre_attachment_reason"] == "ambiguous_back_reference_requires_manager"
    assert ambiguous["shadow_created"] is True
    assert ambiguous["shadow_role"] == "tentative_non_authoritative"
    assert ambiguous["fixture_manager_decision_source"] == "fixture_manager_structured_decision"
    assert ambiguous["deterministic_selected_target"] is False
    assert ambiguous["mutation_authority"] is False

    named = by_id["named_item_correction"]
    assert named["pre_attachment_disposition"] == "target_committed_thread"
    assert named["shadow_created"] is False
    assert named["shadow_skip_reason"] == "already_safe_pass"

    pending = by_id["pending_followup_answer"]
    assert pending["pre_attachment_disposition"] == "attach_existing_thread"
    assert pending["shadow_created"] is False
    assert pending["shadow_skip_reason"] == "resolved_pending_followup"

    query = by_id["previous_drink_calorie_query"]
    assert query["fixture_manager_workflow_effect"] == "query_no_mutation"
    assert query["query_no_mutation"] is True
    assert query["mutation_authority"] is False

    target_update = by_id["explicit_daily_target_1800"]
    assert target_update["fixture_manager_workflow_effect"] == "daily_target_update_candidate"
    assert target_update["target_update_requires_manager_decision"] is True
    assert target_update["mutation_authority"] is False

    meal_estimate = by_id["meal_estimate_800_not_target"]
    assert meal_estimate["fixture_manager_workflow_effect"] == "meal_estimate_context"
    assert meal_estimate["target_update_requires_manager_decision"] is False
    assert meal_estimate["mutation_authority"] is False


def test_fake_provider_context_smoke_script_writes_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "fake_context_smoke.json"

    from scripts.run_accurate_intake_fake_provider_context_smoke import main

    exit_code = main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["live_provider_called"] is False
