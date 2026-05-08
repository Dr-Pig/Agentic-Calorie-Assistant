from __future__ import annotations

import json
from pathlib import Path

from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE,
)

from app.composition.accurate_intake_current_shell_claim_boundary import (
    build_current_shell_appshell_claim_boundary,
)
from app.composition.accurate_intake_pl_ce_product_pages_self_use_flow_gate import (
    REQUIRED_INPUTS,
    build_pl_ce_product_pages_self_use_flow_gate_artifact,
)


def _valid_inputs() -> dict[str, dict[str, object]]:
    return {
        "ui_same_truth_contract": {
            "artifact_type": "accurate_intake_ui_same_truth_render_contract",
            "status": "pass",
            "frontend_render_only": True,
            "frontend_semantic_owner": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "today_macro_runtime_mirror_gate": {
            "artifact_type": "accurate_intake_today_macro_runtime_mirror_gate",
            "status": "today_macro_runtime_mirror_gate_ready_for_browser",
            "pass_type": "runtime_backed",
            "blockers": [],
            "macro_visible_case_checked": True,
            "macro_guarded_case_checked": True,
            "backend_macro_fields_required": True,
            "show_macro_false_suppresses_macro": True,
            "frontend_macro_math_used": False,
            "assistant_text_macro_parsed": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "product_pages_renderer_source_map": {
            "artifact_type": "accurate_intake_product_pages_renderer_source_map",
            "status": "product_pages_renderer_source_map_ready_for_human_review",
            "blockers": [],
            "render_only_boundary_ok": True,
            "frontend_semantic_owner": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "summary": {
                "page_count": 3,
                "selector_count": 33,
                "endpoint_count": 8,
                "backend_field_count": 30,
            },
        },
        "product_pages_renderer_source_closure_gate": {
            "artifact_type": "accurate_intake_product_pages_renderer_source_closure_gate",
            "status": "product_pages_renderer_source_closure_ready_for_browser",
            "pass_type": "contract",
            "blockers": [],
            "route_table_checked": True,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "frontend_semantic_owner": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "summary": {
                "page_count": 3,
                "manager_runtime_gates_checked": 5,
                "endpoint_method_contract_count": 11,
                "route_endpoint_count": 11,
            },
        },
        "product_pages_browser_smoke": {
            "smoke_id": "accurate_intake_product_pages_browser_smoke_v1",
            "status": "pass",
            "browser_executed": True,
            "local_date": "2026-05-05",
            "chat_page_loaded": True,
            "chat_sent_cjk_message": True,
            "chat_assistant_bubble_rendered": True,
            "chat_history_reloaded": True,
            "chat_scroll_behavior_checked": True,
            "chat_reload_scroll_behavior_checked": True,
            "chat_no_debug_trace": True,
            "today_page_loaded": True,
            "today_date_switch_checked": True,
            "today_summary_rendered": True,
            "today_meal_list_rendered": True,
            "today_no_debug_trace": True,
            "body_page_loaded": True,
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
            "manager_provider_call_count": 0,
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
        "product_pages_context_target_browser_closure": {
            "artifact_type": "accurate_intake_product_pages_context_target_browser_closure",
            "status": "context_target_browser_closure_ready_for_self_use_flow_gate",
            "pass_type": "browser_executed",
            "blockers": [],
            "browser_executed": True,
            "context_engineering_present": True,
            "session_state_injected": True,
            "pending_meal_or_correction_context_present": True,
            "target_candidate_list_read_only": True,
            "context_strip_read_only": True,
            "target_candidate_count_rendered": 2,
            "target_candidate_names_rendered": ["luwei", "milk tea"],
            "frontend_semantic_owner": False,
            "frontend_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
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
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
    }


def test_product_pages_self_use_flow_gate_accepts_complete_fixture_browser_chain() -> None:
    artifact = build_pl_ce_product_pages_self_use_flow_gate_artifact(_valid_inputs())
    claim_boundary = build_current_shell_appshell_claim_boundary()

    assert artifact["artifact_type"] == CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE
    assert artifact["status"] == "product_pages_self_use_flow_ready_for_human_review"
    assert artifact["pass_type"] == "contract"
    assert artifact["current_shell_sync_contract_source"] == claim_boundary["current_shell_sync_contract_source"]
    assert artifact["manager_runtime_gate_ledger_source"] == claim_boundary["manager_runtime_gate_ledger_source"]
    assert artifact["appshell_claim_boundary"]["status"] == claim_boundary["status"]
    assert artifact["required_inputs"] == list(REQUIRED_INPUTS)
    assert artifact["blockers"] == []
    assert artifact["summary"]["pages_verified"] == ["chat", "today", "body"]
    assert artifact["summary"]["three_distinct_pages_verified"] is True
    assert artifact["summary"]["seven_day_diary_checked"] is True
    assert artifact["summary"]["short_term_context_checked"] is True
    assert artifact["summary"]["target_candidate_ui_checked"] is True
    assert artifact["summary"]["today_macro_runtime_mirror_checked"] is True
    assert artifact["summary"]["renderer_source_closure_checked"] is True
    assert artifact["summary"]["context_target_browser_closure_checked"] is True
    assert artifact["summary"]["body_noplan_degraded_checked"] is True
    assert artifact["summary"]["fixture_product_loop_steps_checked"] == 10
    assert artifact["summary"]["strongest_consumed_pass_type"] == "browser_executed"
    assert artifact["all_required_browser_artifacts_executed"] is True
    assert artifact["browser_executed_required"] is True
    assert artifact["blocked_browser_is_not_pass"] is True
    assert artifact["frontend_render_only"] is True
    assert artifact["frontend_semantic_owner"] is False
    assert "ready_for_live_diagnostic_decision" not in artifact
    assert "ready_for_fdb_integration" not in artifact
    assert artifact["fixture_evidence_used"] is True
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["real_fooddb_pass_claimed"] is False
    assert artifact["dogfood_pass"] is False
    assert "web_readiness_claimed" not in artifact
    assert "product_readiness_claimed" not in artifact
    assert "private_self_use_approved" not in artifact


def test_product_pages_self_use_flow_gate_reports_runtime_claim_dependency_without_inventing_runtime_pass() -> None:
    artifact = build_pl_ce_product_pages_self_use_flow_gate_artifact(_valid_inputs())
    boundary = artifact["appshell_claim_boundary"]

    assert artifact["pass_type"] == "contract"
    assert boundary["appshell_rules"]["runtime_backed_requires_upstream_gate_green"] is True
    assert boundary["appshell_rules"]["browser_executed_requires_upstream_gate_green"] is True
    if boundary["non_green_manager_runtime_gates"]:
        assert boundary["runtime_backed_claim_ready"] is False
        assert boundary["browser_executed_claim_ready"] is False
        assert boundary["status"] == "blocked_on_manager_runtime_upstream_gates"


def test_product_pages_self_use_flow_gate_blocks_optional_browser_blocked_state() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_visual_qa"]["status"] = "blocked"
    inputs["product_pages_visual_qa"]["browser_executed"] = False

    artifact = build_pl_ce_product_pages_self_use_flow_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_visual_qa.unexpected_status:blocked" in artifact["blockers"]
    assert "product_pages_visual_qa.browser_not_executed" in artifact["blockers"]
    assert artifact["all_required_browser_artifacts_executed"] is False
    assert "product_readiness_claimed" not in artifact


def test_product_pages_self_use_flow_gate_blocks_semantic_or_truth_overclaims() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_target_candidate_ui_smoke"]["frontend_selected_target"] = True
    inputs["product_pages_short_term_context_smoke"]["deterministic_semantic_inference_used"] = True
    inputs["fixture_full_product_loop_e2e"]["ready_for_fdb_integration"] = True
    inputs["fixture_full_product_loop_e2e"]["dogfood_pass"] = True

    artifact = build_pl_ce_product_pages_self_use_flow_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_target_candidate_ui_smoke.frontend_selected_target" in artifact["blockers"]
    assert "product_pages_short_term_context_smoke.deterministic_semantic_inference_used" in artifact["blockers"]
    assert "fixture_full_product_loop_e2e.ready_for_fdb_integration" in artifact["blockers"]
    assert "fixture_full_product_loop_e2e.dogfood_pass" in artifact["blockers"]
    assert "ready_for_fdb_integration" not in artifact


def test_product_pages_self_use_flow_gate_blocks_missing_target_candidate_or_context_flow() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_target_candidate_ui_smoke"]["target_candidate_surface_checked"] = False
    inputs["product_pages_short_term_context_smoke"]["pending_followup_reloaded"] = False
    inputs["fixture_full_product_loop_e2e"]["completed_product_loop_steps"] = ["target_update"]

    artifact = build_pl_ce_product_pages_self_use_flow_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_target_candidate_ui_smoke.target_candidate_surface_checked_not_true" in artifact["blockers"]
    assert "product_pages_short_term_context_smoke.pending_followup_reloaded_not_true" in artifact["blockers"]
    assert "fixture_full_product_loop_e2e.completed_step_missing:food_log" in artifact["blockers"]
    assert "fixture_full_product_loop_e2e.completed_step_missing:fake_provider_context_smoke" in artifact["blockers"]


def test_product_pages_self_use_flow_gate_requires_runtime_and_browser_closure_inputs() -> None:
    inputs = _valid_inputs()
    inputs["today_macro_runtime_mirror_gate"]["status"] = "blocked"
    inputs["product_pages_renderer_source_closure_gate"]["route_table_checked"] = False
    inputs["product_pages_body_noplan_degraded_smoke"]["browser_executed"] = False
    inputs["product_pages_context_target_browser_closure"]["context_engineering_present"] = False

    artifact = build_pl_ce_product_pages_self_use_flow_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "today_macro_runtime_mirror_gate.unexpected_status:blocked" in artifact["blockers"]
    assert (
        "product_pages_renderer_source_closure_gate.route_table_checked_not_true"
        in artifact["blockers"]
    )
    assert "product_pages_body_noplan_degraded_smoke.browser_not_executed" in artifact["blockers"]
    assert (
        "product_pages_context_target_browser_closure.context_engineering_present_not_true"
        in artifact["blockers"]
    )
    assert artifact["summary"]["today_macro_runtime_mirror_checked"] is False
    assert artifact["summary"]["renderer_source_closure_checked"] is False
    assert artifact["summary"]["context_target_browser_closure_checked"] is False
    assert artifact["summary"]["body_noplan_degraded_checked"] is False


def test_product_pages_self_use_flow_gate_cli_writes_from_existing_artifacts(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.build_current_shell_compatibility_product_pages_self_use_flow_gate import main

    output_path = tmp_path / "self-use-flow.json"
    args = ["--output", str(output_path)]
    for group_id, payload in _valid_inputs().items():
        artifact_path = tmp_path / f"{group_id}.json"
        artifact_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        args.extend(["--artifact", f"{group_id}={artifact_path}"])

    exit_code = main(args)
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed["status"] == "product_pages_self_use_flow_ready_for_human_review"
    assert artifact["status"] == "product_pages_self_use_flow_ready_for_human_review"


def test_product_pages_self_use_flow_gate_source_stays_out_of_forbidden_boundaries() -> None:
    source_paths = (
        Path("app/composition/accurate_intake_pl_ce_product_pages_self_use_flow_gate.py"),
        Path("scripts/build_current_shell_compatibility_product_pages_self_use_flow_gate.py"),
        Path("scripts/build_accurate_intake_pl_ce_product_pages_self_use_flow_gate.py"),
    )
    forbidden = (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "ManagerContextPacket",
        "TavilyClient",
        "BuilderSpaceAdapter",
        "mutation_legality",
        "selected_extract",
    )
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in source


def test_ci_keeps_product_pages_self_use_flow_gate_out_of_required_merge_path() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "product-pages-browser-e2e" in workflow
    assert "tests/test_current_shell_compatibility_product_pages_self_use_flow_gate.py" in workflow
    assert "tests/test_accurate_intake_pl_ce_product_pages_self_use_flow_gate.py" not in workflow
    assert "build_accurate_intake_pl_ce_product_pages_self_use_flow_gate.py" not in workflow
    assert "ui_same_truth_contract=artifacts/accurate_intake_ui_same_truth_render_contract_ci.json" not in workflow
    assert (
        "product_pages_target_candidate_ui_smoke="
        "artifacts/accurate_intake_product_pages_target_candidate_ui_smoke_ci.json"
    ) not in workflow
    assert "fixture_full_product_loop_e2e=artifacts/accurate_intake_fixture_full_product_loop_e2e_ci.json" not in workflow
    assert "artifacts/accurate_intake_pl_ce_product_pages_self_use_flow_gate_ci.json" not in workflow
