from __future__ import annotations

import json
from pathlib import Path

from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE,
)
from app.composition.current_shell_fooddb_triad_same_truth_contract import (
    EXPECTED_FOODDB_TRIAD_SAME_TRUTH_CASES,
    FOODDB_TRIAD_SAME_TRUTH_REQUIRED_NON_CLAIMS,
)

from app.composition.accurate_intake_current_shell_claim_boundary import (
    build_current_shell_appshell_claim_boundary,
)
from app.composition.accurate_intake_pl_ce_browser_activation_evidence_gate import (
    build_pl_ce_browser_activation_evidence_gate_artifact,
)


def _valid_inputs() -> dict[str, dict[str, object]]:
    return {
        "current_shell_compatibility_local_mvp_candidate_bundle": {
            "artifact_type": "accurate_intake_current_shell_compatibility_local_mvp_candidate_bundle",
            "status": "current_shell_compatibility_local_mvp_candidate_ready_for_human_review",
            "activation_gate_status": "blocked_pending_human_and_browser_activation",
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "product_pages_browser_smoke": {
            "smoke_id": "accurate_intake_product_pages_browser_smoke_v1",
            "status": "pass",
            "browser_executed": True,
            "local_date": "2026-05-05",
            "chat_page_loaded": True,
            "today_page_loaded": True,
            "body_page_loaded": True,
            "chat_sent_cjk_message": True,
            "chat_assistant_bubble_rendered": True,
            "chat_history_reloaded": True,
            "chat_scroll_behavior_checked": True,
            "chat_reload_scroll_behavior_checked": True,
            "today_date_switch_checked": True,
            "today_summary_rendered": True,
            "today_meal_list_rendered": True,
            "macro_present_exact_item_browser_checked": True,
            "macro_missing_exact_item_browser_checked": True,
            "route_backed_macro_browser_checked": True,
            "route_backed_macro_present_current_budget": {
                "consumed_kcal": 300,
                "consumed_protein": 12,
                "consumed_carbs": 48,
                "consumed_fat": 6,
                "show_macro": True,
                "macro_guard_reason": "committed_and_aligned",
            },
            "route_backed_macro_missing_current_budget": {
                "consumed_kcal": 130,
                "consumed_protein": 0,
                "consumed_carbs": 0,
                "consumed_fat": 0,
                "show_macro": False,
                "macro_guard_reason": "no_macro_data",
            },
            "route_backed_macro_non_claims": {
                "live_llm_invoked": False,
                "web_tavily_used": False,
                "fooddb_truth_updated": False,
                "product_readiness_claimed": False,
                "private_self_use_approved": False,
            },
            "fooddb_triad_same_truth_browser_checked": True,
            "fooddb_triad_same_truth_cases": EXPECTED_FOODDB_TRIAD_SAME_TRUTH_CASES,
            "fooddb_triad_same_truth_non_claims": {
                flag: False for flag in FOODDB_TRIAD_SAME_TRUTH_REQUIRED_NON_CLAIMS
            },
            "body_active_plan_rendered": True,
            "body_plan_form_saved": True,
            "body_plan_readback_checked": True,
            "body_plan_read_model_fields_rendered": True,
            "body_budget_read_models_rendered": True,
            "body_manual_target_saved": True,
            "body_weight_checkin_saved": True,
            "body_latest_weight_rendered_from_backend": True,
            "body_weight_history_date_scoped_readback": True,
            "body_manual_target_read_model_rendered": True,
            "body_plan_read_model_values": {
                "daily_target": "1550 kcal",
                "tdee": "1819 kcal",
                "current_weight": "70 kg",
                "target_weight": "65 kg",
                "activity": "light",
                "goal": "Lose weight",
                "weight_history": "2026-05-05 | 70.4 kg",
            },
            "body_budget_read_model_values": {
                "active_target": "1550 kcal",
                "consumed": "400 kcal",
                "remaining": "1150 kcal",
                "estimated_deficit": "269 kcal",
                "effective_budget": "1550 kcal",
                "weekly_progress": "400 kcal consumed",
            },
            "today_manual_target_readback_checked": True,
            "body_session_status_rendered": True,
            "today_session_status_rendered": True,
            "body_no_debug_trace": True,
            "today_no_debug_trace": True,
            "desktop_no_overflow": True,
            "mobile_no_overflow": True,
            "mobile_populated_state_checked": True,
            "product_cjk_copy_rendered": True,
            "nav_session_query_preserved": True,
            "forbidden_storage_used": False,
            "frontend_semantic_owner": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "production_db_used": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "product_pages_seven_day_diary_smoke": {
            "smoke_id": "accurate_intake_product_pages_seven_day_diary_smoke_v1",
            "status": "pass",
            "browser_executed": True,
            "seven_day_window_checked": True,
            "day_count_checked": 7,
            "per_day_diary_isolated": True,
            "per_day_budget_values_checked": True,
            "today_date_strip_checked": True,
            "today_nav_date_preserved": True,
            "today_chat_link_date_preserved": True,
            "desktop_no_overflow": True,
            "mobile_no_overflow": True,
            "forbidden_storage_used": False,
            "frontend_semantic_owner": False,
            "manager_provider_call_count": 0,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "production_db_used": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "product_pages_short_term_context_smoke": {
            "smoke_id": "accurate_intake_product_pages_short_term_context_smoke_v1",
            "status": "pass",
            "browser_executed": True,
            "browser_reload_checked": True,
            "fixture_manager_used": True,
            "pending_followup_created": True,
            "pending_followup_reloaded": True,
            "context_policy_version_present": True,
            "loaded_context_summary_present": True,
            "omitted_context_summary_present": True,
            "pending_pins_present_after_followup": True,
            "chat_history_context_fields_reloaded": True,
            "chat_cjk_roundtrip_rendered": True,
            "assistant_followup_bubble_rendered": True,
            "assistant_commit_bubble_rendered": True,
            "today_same_day_meal_rendered": True,
            "today_summary_rendered": True,
            "product_pages_no_debug_trace": True,
            "frontend_semantic_owner": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "product_pages_target_candidate_ui_smoke": {
            "smoke_id": "accurate_intake_product_pages_target_candidate_ui_smoke_v1",
            "status": "pass",
            "browser_executed": True,
            "browser_reload_checked": True,
            "chat_page_loaded": True,
            "chat_history_reloaded": True,
            "target_candidate_surface_checked": True,
            "target_candidate_count_rendered": 2,
            "target_candidate_names_rendered": ["luwei", "milk tea"],
            "target_candidate_list_read_only": True,
            "context_strip_read_only": True,
            "product_pages_no_debug_trace": True,
            "manager_provider_call_count": 0,
            "frontend_semantic_owner": False,
            "frontend_selected_target": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "product_pages_visual_qa": {
            "artifact_type": "accurate_intake_product_pages_visual_qa",
            "status": "pass",
            "browser_executed": True,
            "desktop_screenshots_captured": True,
            "mobile_screenshots_captured": True,
            "chat_surface_verified": True,
            "today_surface_verified": True,
            "body_surface_verified": True,
            "three_distinct_pages_verified": True,
            "desktop_no_overflow": True,
            "mobile_no_overflow": True,
            "visible_trace_debug_terms_absent": True,
            "forbidden_storage_used": False,
            "frontend_semantic_owner": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "production_db_used": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "product_pages_body_noplan_degraded_smoke": {
            "smoke_id": "accurate_intake_product_pages_body_noplan_degraded_smoke_v1",
            "status": "pass",
            "browser_executed": True,
            "body_page_loaded": True,
            "today_page_loaded": True,
            "no_plan_body_status_rendered": True,
            "body_targets_hidden_for_no_plan": True,
            "body_budget_degraded_rendered": True,
            "today_no_plan_budget_rendered": True,
            "no_bootstrap_or_mutation_post": True,
            "product_pages_no_debug_trace": True,
            "body_values": {
                "status": "Set up your body plan to see targets.",
                "daily_target": "--",
                "tdee": "--",
                "active_target": "--",
                "remaining": "--",
            },
            "today_values": {
                "budget": "0",
                "consumed": "0",
                "remaining": "0",
            },
            "frontend_semantic_owner": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "production_db_used": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "fixture_full_product_loop_e2e": {
            "artifact_type": "accurate_intake_fixture_full_product_loop_e2e",
            "status": "fixture_product_loop_e2e_diagnostic_pass",
            "completed_product_loop_steps": [
                "target_update",
                "food_log",
                "listed_basket_commit",
                "correction",
                "removal",
                "remaining_query",
                "reload_continuity",
                "browser_render_same_truth",
                "context_replay",
                "fake_provider_context_smoke",
            ],
            "browser_executed": True,
            "ready_for_fdb_integration": False,
            "fixture_evidence_used": True,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_db_used": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "manager_context_packet_schema_changed": False,
            "frontend_semantic_owner": False,
        },
        "product_pages_self_use_flow_gate": {
            "artifact_type": CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE,
            "status": "product_pages_self_use_flow_ready_for_human_review",
            "pass_type": "contract",
            "all_required_browser_artifacts_executed": True,
            "browser_executed_required": True,
            "frontend_semantic_owner": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "summary": {
                "three_distinct_pages_verified": True,
                "seven_day_diary_checked": True,
                "short_term_context_checked": True,
                "target_candidate_ui_checked": True,
                "today_macro_runtime_mirror_checked": True,
                "route_backed_macro_budget_truth_checked": True,
                "fooddb_triad_same_truth_checked": True,
                "renderer_source_closure_checked": True,
                "context_target_browser_closure_checked": True,
                "body_noplan_degraded_checked": True,
                "strongest_consumed_pass_type": "browser_executed",
                "fixture_product_loop_steps_checked": 10,
            },
        },
    }


def test_browser_activation_gate_requires_real_browser_evidence_without_readiness_claims() -> None:
    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(_valid_inputs())
    claim_boundary = build_current_shell_appshell_claim_boundary()

    assert artifact["artifact_type"] == CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_ARTIFACT_TYPE
    assert artifact["status"] == "browser_activation_evidence_ready_for_human_review"
    assert artifact["pass_type"] == "contract"
    assert artifact["current_shell_sync_contract_source"] == claim_boundary["current_shell_sync_contract_source"]
    assert artifact["manager_runtime_gate_ledger_source"] == claim_boundary["manager_runtime_gate_ledger_source"]
    assert artifact["appshell_claim_boundary"]["status"] == claim_boundary["status"]
    assert (
        artifact["appshell_claim_boundary"]["browser_executed_claim_ready"]
        == claim_boundary["browser_executed_claim_ready"]
    )
    assert artifact["browser_executed_required"] is True
    assert artifact["all_required_browser_artifacts_executed"] is True
    assert artifact["summary"]["browser_artifact_count"] == 6
    assert artifact["summary"]["requires_target_candidate_ui"] is True
    assert artifact["summary"]["requires_fixture_full_product_loop_e2e"] is True
    assert artifact["summary"]["requires_body_noplan_degraded_browser"] is True
    assert artifact["summary"]["requires_product_pages_self_use_flow_gate"] is True
    assert artifact["summary"]["self_use_flow_gate_checked"] is True
    assert artifact["summary"]["self_use_flow_gate_strongest_pass_type"] == "browser_executed"
    assert artifact["summary"]["fixture_product_loop_step_count"] == 10
    assert "ready_for_live_diagnostic_decision" not in artifact
    assert "ready_for_fdb_integration" not in artifact
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["real_fooddb_pass_claimed"] is False
    assert artifact["dogfood_pass"] is False
    assert "web_readiness_claimed" not in artifact
    assert "product_readiness_claimed" not in artifact
    assert "private_self_use_approved" not in artifact
    assert artifact["blockers"] == []


def test_browser_activation_gate_accepts_legacy_local_mvp_bundle_identity() -> None:
    inputs = _valid_inputs()
    local_mvp = inputs["current_shell_compatibility_local_mvp_candidate_bundle"]
    local_mvp["artifact_type"] = "accurate_intake_pl_ce_local_mvp_candidate_bundle"
    local_mvp["status"] = "pl_ce_local_mvp_candidate_ready_for_human_review"

    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(inputs)

    assert artifact["status"] == "browser_activation_evidence_ready_for_human_review"
    assert artifact["blockers"] == []


def test_browser_activation_gate_reports_contract_only_boundary_when_upstream_runtime_claims_are_pending() -> None:
    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(_valid_inputs())
    boundary = artifact["appshell_claim_boundary"]

    assert artifact["pass_type"] == "contract"
    assert boundary["current_shell_in_scope_journeys"] == ["A", "B", "C", "D", "E", "G", "H", "J", "K"]
    assert "browser_executed" in boundary["pass_taxonomy"]
    assert boundary["appshell_rules"]["browser_executed_requires_upstream_gate_green"] is True
    if boundary["non_green_manager_runtime_gates"]:
        assert boundary["browser_executed_claim_ready"] is False
        assert boundary["status"] == "blocked_on_manager_runtime_upstream_gates"


def test_browser_activation_gate_blocks_missing_or_blocked_browser_execution() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_browser_smoke"]["browser_executed"] = False
    inputs["product_pages_browser_smoke"]["status"] = "blocked"

    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_browser_smoke.unexpected_status:blocked" in artifact["blockers"]
    assert "product_pages_browser_smoke.browser_not_executed" in artifact["blockers"]
    assert artifact["all_required_browser_artifacts_executed"] is False
    assert "ready_for_live_diagnostic_decision" not in artifact


def test_browser_activation_gate_blocks_swapped_identity_and_unknown_mvp_candidate() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_seven_day_diary_smoke"]["smoke_id"] = "accurate_intake_product_pages_browser_smoke_v1"
    inputs["current_shell_compatibility_local_mvp_candidate_bundle"]["artifact_type"] = "wrong"

    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_seven_day_diary_smoke.unexpected_smoke_id:accurate_intake_product_pages_browser_smoke_v1" in artifact["blockers"]
    assert "current_shell_compatibility_local_mvp_candidate_bundle.unexpected_artifact_type:wrong" in artifact["blockers"]


def test_browser_activation_gate_blocks_frontend_semantics_live_or_fooddb_claims() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_short_term_context_smoke"]["deterministic_semantic_inference_used"] = True
    inputs["product_pages_visual_qa"]["frontend_semantic_owner"] = True
    inputs["product_pages_browser_smoke"]["fooddb_evidence_used"] = True
    inputs["product_pages_seven_day_diary_smoke"]["manager_provider_call_count"] = 1
    inputs["product_pages_target_candidate_ui_smoke"]["frontend_selected_target"] = True

    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_short_term_context_smoke.deterministic_semantic_inference_used" in artifact["blockers"]
    assert "product_pages_visual_qa.frontend_semantic_owner" in artifact["blockers"]
    assert "product_pages_browser_smoke.fooddb_evidence_used" in artifact["blockers"]
    assert "product_pages_seven_day_diary_smoke.manager_provider_called" in artifact["blockers"]
    assert "product_pages_target_candidate_ui_smoke.frontend_selected_target" in artifact["blockers"]


def test_browser_activation_gate_blocks_missing_target_candidate_or_fixture_loop_evidence() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_target_candidate_ui_smoke"]["target_candidate_surface_checked"] = False
    inputs["product_pages_target_candidate_ui_smoke"]["target_candidate_count_rendered"] = 1
    inputs["product_pages_target_candidate_ui_smoke"]["target_candidate_names_rendered"] = ["luwei"]
    inputs["product_pages_target_candidate_ui_smoke"]["manager_provider_call_count"] = 1
    inputs["fixture_full_product_loop_e2e"]["completed_product_loop_steps"] = ["target_update"]
    inputs["fixture_full_product_loop_e2e"]["fixture_evidence_used"] = False

    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_target_candidate_ui_smoke.target_candidate_surface_checked_not_true" in artifact["blockers"]
    assert "product_pages_target_candidate_ui_smoke.target_candidate_count_too_low" in artifact["blockers"]
    assert "product_pages_target_candidate_ui_smoke.target_candidate_missing:milk tea" in artifact["blockers"]
    assert "product_pages_target_candidate_ui_smoke.manager_provider_called" in artifact["blockers"]
    assert "fixture_full_product_loop_e2e.fixture_evidence_used_not_true" in artifact["blockers"]
    assert "fixture_full_product_loop_e2e.completed_step_missing:food_log" in artifact["blockers"]
    assert "fixture_full_product_loop_e2e.completed_step_missing:fake_provider_context_smoke" in artifact["blockers"]


def test_browser_activation_gate_blocks_missing_self_use_flow_or_body_noplan_evidence() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_self_use_flow_gate"]["status"] = "blocked"
    inputs["product_pages_self_use_flow_gate"]["summary"][  # type: ignore[index]
        "context_target_browser_closure_checked"
    ] = False
    inputs["product_pages_self_use_flow_gate"]["summary"][  # type: ignore[index]
        "strongest_consumed_pass_type"
    ] = "contract"
    inputs["product_pages_body_noplan_degraded_smoke"]["browser_executed"] = False
    inputs["product_pages_body_noplan_degraded_smoke"]["body_values"][  # type: ignore[index]
        "daily_target"
    ] = "1550 kcal"

    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_self_use_flow_gate.unexpected_status:blocked" in artifact["blockers"]
    assert (
        "product_pages_self_use_flow_gate.context_target_browser_closure_not_checked"
        in artifact["blockers"]
    )
    assert "product_pages_self_use_flow_gate.strongest_pass_type_not_browser_executed" in artifact["blockers"]
    assert "product_pages_body_noplan_degraded_smoke.browser_not_executed" in artifact["blockers"]
    assert (
        "product_pages_body_noplan_degraded_smoke.body_daily_target_not_hidden"
        in artifact["blockers"]
    )
    assert artifact["summary"]["self_use_flow_gate_checked"] is False


def test_browser_activation_gate_blocks_stale_body_read_model_values() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_browser_smoke"]["body_plan_read_model_values"] = {
        "daily_target": "1312 kcal",
        "tdee": "9999 kcal",
        "current_weight": "69 kg",
        "target_weight": "64 kg",
        "activity": "sedentary",
        "goal": "Maintain weight",
        "weight_history": "",
    }

    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:daily_target" in artifact["blockers"]
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:tdee" in artifact["blockers"]
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:current_weight" in artifact["blockers"]
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:target_weight" in artifact["blockers"]
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:activity" in artifact["blockers"]
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:goal" in artifact["blockers"]
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:weight_history" in artifact["blockers"]


def test_browser_activation_gate_requires_product_pages_macro_browser_evidence() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_browser_smoke"].pop("macro_present_exact_item_browser_checked", None)
    inputs["product_pages_browser_smoke"].pop("macro_missing_exact_item_browser_checked", None)

    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_browser_smoke.macro_present_exact_item_browser_checked_not_true" in artifact["blockers"]
    assert "product_pages_browser_smoke.macro_missing_exact_item_browser_checked_not_true" in artifact["blockers"]


def test_browser_activation_gate_requires_route_backed_macro_budget_truth() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_browser_smoke"]["route_backed_macro_browser_checked"] = False
    inputs["product_pages_browser_smoke"]["route_backed_macro_missing_current_budget"] = {
        "consumed_kcal": 130,
        "consumed_protein": 0,
        "consumed_carbs": 0,
        "consumed_fat": 1,
        "show_macro": False,
        "macro_guard_reason": "no_macro_data",
    }
    inputs["product_pages_self_use_flow_gate"]["summary"][  # type: ignore[index]
        "route_backed_macro_budget_truth_checked"
    ] = False

    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_browser_smoke.route_backed_macro_browser_checked_not_true" in artifact["blockers"]
    assert (
        "product_pages_browser_smoke.route_backed_macro_missing_current_budget_mismatch:consumed_fat"
        in artifact["blockers"]
    )
    assert (
        "product_pages_self_use_flow_gate.route_backed_macro_budget_truth_not_checked"
        in artifact["blockers"]
    )
    assert artifact["summary"]["self_use_flow_gate_checked"] is False


def test_browser_activation_gate_requires_fooddb_triad_same_truth() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_browser_smoke"]["fooddb_triad_same_truth_browser_checked"] = False
    triad_cases = {
        lane: dict(case)
        for lane, case in EXPECTED_FOODDB_TRIAD_SAME_TRUTH_CASES.items()
    }
    triad_cases["listed_component"]["macro_state"] = "visible"
    inputs["product_pages_browser_smoke"]["fooddb_triad_same_truth_cases"] = triad_cases
    inputs["product_pages_self_use_flow_gate"]["summary"][  # type: ignore[index]
        "fooddb_triad_same_truth_checked"
    ] = False

    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert (
        "product_pages_browser_smoke.fooddb_triad_same_truth_browser_checked_not_true"
        in artifact["blockers"]
    )
    assert (
        "product_pages_browser_smoke.fooddb_triad_same_truth_case_mismatch:listed_component:macro_state"
        in artifact["blockers"]
    )
    assert (
        "product_pages_self_use_flow_gate.fooddb_triad_same_truth_not_checked"
        in artifact["blockers"]
    )
    assert artifact["summary"]["self_use_flow_gate_checked"] is False


def test_browser_activation_gate_accepts_browser_smoke_local_date_weight_history() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_browser_smoke"]["local_date"] = "2026-05-06"
    inputs["product_pages_browser_smoke"]["body_plan_read_model_values"]["weight_history"] = (  # type: ignore[index]
        "2026-05-06 | 70.4 kg"
    )

    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(inputs)

    assert artifact["status"] == "browser_activation_evidence_ready_for_human_review"
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:weight_history" not in artifact["blockers"]


def test_browser_activation_gate_cli_writes_from_existing_artifacts(tmp_path: Path) -> None:
    from scripts.build_current_shell_compatibility_browser_activation_evidence_gate import main

    output_path = tmp_path / "browser-activation.json"
    args = ["--output", str(output_path)]
    for group_id, payload in _valid_inputs().items():
        artifact_path = tmp_path / f"{group_id}.json"
        artifact_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        args.extend(["--artifact", f"{group_id}={artifact_path}"])

    exit_code = main(args)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "browser_activation_evidence_ready_for_human_review"
    assert artifact["included_artifact_statuses"]["product_pages_visual_qa"]["source_artifact_path"]


def test_browser_activation_gate_cli_rejects_unknown_artifact_group(tmp_path: Path, capsys) -> None:
    from scripts.build_current_shell_compatibility_browser_activation_evidence_gate import main

    output_path = tmp_path / "browser-activation.json"
    exit_code = main(
        [
            "--artifact",
            f"product_pages_visual_qa_typo={tmp_path / 'visual.json'}",
            "--output",
            str(output_path),
        ]
    )
    printed = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert printed["status"] == "invalid_arguments"
    assert printed["unknown_artifact_groups"] == ["product_pages_visual_qa_typo"]
    assert not output_path.exists()


def test_browser_activation_gate_source_stays_out_of_fooddb_websearch_live_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_pl_ce_browser_activation_evidence_gate.py"),
        Path("scripts/build_current_shell_compatibility_browser_activation_evidence_gate.py"),
        Path("scripts/build_accurate_intake_pl_ce_browser_activation_evidence_gate.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "Tavily",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "kimi",
        "grok",
        "fooddb_evidence_used = True",
        "live_llm_invoked = True",
        "web_tavily_used = True",
        "ready_for_live_diagnostic_decision = True",
    ]
    combined_source = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

    for fragment in forbidden:
        assert fragment not in combined_source


def test_ci_keeps_browser_activation_evidence_gate_out_of_required_merge_path() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "product-pages-browser-e2e" in workflow
    assert "tests/test_current_shell_compatibility_browser_activation_evidence_gate.py" in workflow
    assert "tests/test_accurate_intake_pl_ce_browser_activation_evidence_gate.py" not in workflow
    assert "run_accurate_intake_product_pages_short_term_context_smoke.py --require-browser-execution" in workflow
    assert "run_accurate_intake_product_pages_target_candidate_ui_smoke.py --require-browser-execution" in workflow
    assert "run_accurate_intake_fixture_full_product_loop_e2e.py --require-browser-execution" not in workflow
    assert "build_accurate_intake_pl_ce_browser_activation_evidence_gate.py" not in workflow
    assert "build_current_shell_compatibility_browser_activation_evidence_gate.py" not in workflow
    assert "accurate_intake_pl_ce_browser_activation_evidence_gate_ci.json" not in workflow
