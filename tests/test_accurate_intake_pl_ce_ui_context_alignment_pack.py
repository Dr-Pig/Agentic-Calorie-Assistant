from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_pl_ce_ui_context_alignment_pack import (
    REQUIRED_INPUTS,
    build_pl_ce_ui_context_alignment_pack_artifact,
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
        "context_coverage_matrix": {
            "artifact_type": "accurate_intake_pl_ce_context_coverage_matrix",
            "status": "context_coverage_matrix_ready_for_human_review",
            "blockers": [],
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "summary": {
                "capability_count": 9,
                "covered_capability_count": 9,
                "known_runtime_gap_count": 0,
            },
        },
        "product_pages_browser_smoke": {
            "smoke_id": "accurate_intake_product_pages_browser_smoke_v1",
            "status": "pass",
            "browser_executed": True,
            "local_date": "2026-05-05",
            "chat_page_loaded": True,
            "chat_history_reloaded": True,
            "chat_scroll_behavior_checked": True,
            "chat_no_debug_trace": True,
            "today_page_loaded": True,
            "today_summary_rendered": True,
            "today_meal_list_rendered": True,
            "today_no_debug_trace": True,
            "body_page_loaded": True,
            "body_active_plan_rendered": True,
            "body_plan_readback_checked": True,
            "body_plan_read_model_fields_rendered": True,
            "body_latest_weight_rendered_from_backend": True,
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
            "desktop_no_overflow": True,
            "mobile_no_overflow": True,
            "nav_session_query_preserved": True,
            "forbidden_storage_used": False,
            "frontend_semantic_owner": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
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
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
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
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
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
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
    }


def test_ui_context_alignment_pack_summarizes_three_pages_and_context_evidence() -> None:
    artifact = build_pl_ce_ui_context_alignment_pack_artifact(_valid_inputs())

    assert artifact["artifact_type"] == "accurate_intake_pl_ce_ui_context_alignment_pack"
    assert artifact["status"] == "ui_context_alignment_ready_for_human_review"
    assert artifact["required_inputs"] == list(REQUIRED_INPUTS)
    assert artifact["blockers"] == []
    assert artifact["summary"]["pages_verified"] == ["chat", "today", "body"]
    assert artifact["summary"]["context_covered_capabilities"] == 9
    assert artifact["summary"]["context_known_runtime_gap_count"] == 0
    assert artifact["summary"]["renderer_source_map_page_count"] == 3
    assert artifact["summary"]["renderer_source_map_selector_count"] >= 30
    assert artifact["summary"]["renderer_source_map_endpoint_count"] >= 7
    assert artifact["summary"]["seven_day_diary_checked"] is True
    assert artifact["summary"]["chat_context_reload_checked"] is True
    assert artifact["summary"]["body_read_model_checked"] is True
    assert artifact["render_only_boundary_ok"] is True
    assert artifact["context_engineering_fault_claimed"] is False
    assert artifact["review_required_before_provider_call"] is True
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["ready_for_fdb_integration"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False


def test_ui_context_alignment_pack_blocks_missing_or_blocked_context_matrix() -> None:
    inputs = _valid_inputs()
    inputs["context_coverage_matrix"]["blockers"] = ["coverage.pending_followup_carryover.missing"]

    artifact = build_pl_ce_ui_context_alignment_pack_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_coverage_matrix.upstream_blockers_present" in artifact["blockers"]


def test_ui_context_alignment_pack_blocks_missing_or_blocked_renderer_source_map() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_renderer_source_map"]["blockers"] = ["today.missing_selector:#meal-list"]

    artifact = build_pl_ce_ui_context_alignment_pack_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_renderer_source_map.upstream_blockers_present" in artifact["blockers"]


def test_ui_context_alignment_pack_accepts_context_known_runtime_gap_status_without_fault_claim() -> None:
    inputs = _valid_inputs()
    inputs["context_coverage_matrix"]["status"] = "context_coverage_matrix_ready_with_known_runtime_gaps"
    inputs["context_coverage_matrix"]["summary"] = {
        "capability_count": 9,
        "covered_capability_count": 9,
        "known_runtime_gap_count": 1,
    }

    artifact = build_pl_ce_ui_context_alignment_pack_artifact(inputs)

    assert artifact["status"] == "ui_context_alignment_ready_for_human_review"
    assert artifact["summary"]["context_known_runtime_gap_count"] == 1
    assert artifact["context_engineering_fault_claimed"] is False
    assert artifact["ready_for_live_diagnostic_decision"] is False


def test_ui_context_alignment_pack_blocks_browser_or_page_alignment_gaps() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_browser_smoke"]["body_plan_readback_checked"] = False
    inputs["product_pages_browser_smoke"]["body_plan_read_model_fields_rendered"] = False
    inputs["product_pages_browser_smoke"]["body_latest_weight_rendered_from_backend"] = False
    inputs["product_pages_browser_smoke"]["body_manual_target_read_model_rendered"] = False
    inputs["product_pages_seven_day_diary_smoke"]["day_count_checked"] = 6
    inputs["product_pages_short_term_context_smoke"]["chat_history_context_fields_reloaded"] = False
    inputs["product_pages_visual_qa"]["today_surface_verified"] = False

    artifact = build_pl_ce_ui_context_alignment_pack_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_browser_smoke.body_plan_readback_checked_not_true" in artifact["blockers"]
    assert "product_pages_browser_smoke.body_plan_read_model_fields_rendered_not_true" in artifact["blockers"]
    assert "product_pages_browser_smoke.body_latest_weight_rendered_from_backend_not_true" in artifact["blockers"]
    assert "product_pages_browser_smoke.body_manual_target_read_model_rendered_not_true" in artifact["blockers"]
    assert "product_pages_seven_day_diary_smoke.seven_day_window_incomplete" in artifact["blockers"]
    assert (
        "product_pages_short_term_context_smoke.chat_history_context_fields_reloaded_not_true"
        in artifact["blockers"]
    )
    assert "product_pages_visual_qa.today_surface_verified_not_true" in artifact["blockers"]


def test_ui_context_alignment_pack_blocks_stale_body_read_model_values() -> None:
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

    artifact = build_pl_ce_ui_context_alignment_pack_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:daily_target" in artifact["blockers"]
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:tdee" in artifact["blockers"]
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:current_weight" in artifact["blockers"]
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:target_weight" in artifact["blockers"]
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:activity" in artifact["blockers"]
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:goal" in artifact["blockers"]
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:weight_history" in artifact["blockers"]


def test_ui_context_alignment_pack_accepts_browser_smoke_local_date_weight_history() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_browser_smoke"]["local_date"] = "2026-05-06"
    inputs["product_pages_browser_smoke"]["body_plan_read_model_values"]["weight_history"] = (  # type: ignore[index]
        "2026-05-06 | 70.4 kg"
    )

    artifact = build_pl_ce_ui_context_alignment_pack_artifact(inputs)

    assert artifact["status"] == "ui_context_alignment_ready_for_human_review"
    assert "product_pages_browser_smoke.body_read_model_value_mismatch:weight_history" not in artifact["blockers"]


def test_ui_context_alignment_pack_blocks_frontend_or_live_truth_overclaims() -> None:
    inputs = _valid_inputs()
    inputs["ui_same_truth_contract"]["frontend_semantic_owner"] = True
    inputs["context_coverage_matrix"]["deterministic_selected_target"] = True
    inputs["product_pages_short_term_context_smoke"]["raw_text_intent_router_used"] = True
    inputs["product_pages_visual_qa"]["product_readiness_claimed"] = True

    artifact = build_pl_ce_ui_context_alignment_pack_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "ui_same_truth_contract.frontend_semantic_owner" in artifact["blockers"]
    assert "context_coverage_matrix.deterministic_selected_target" in artifact["blockers"]
    assert "product_pages_short_term_context_smoke.raw_text_intent_router_used" in artifact["blockers"]
    assert "product_pages_visual_qa.product_readiness_claimed" in artifact["blockers"]


def test_ui_context_alignment_pack_cli_writes_from_existing_artifacts(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_pl_ce_ui_context_alignment_pack import main

    output_path = tmp_path / "ui-context-alignment.json"
    args = ["--output", str(output_path)]
    for group_id, payload in _valid_inputs().items():
        artifact_path = tmp_path / f"{group_id}.json"
        artifact_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        args.extend(["--artifact", f"{group_id}={artifact_path}"])

    exit_code = main(args)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "ui_context_alignment_ready_for_human_review"
    assert artifact["included_artifact_statuses"]["context_coverage_matrix"]["source_artifact_path"]


def test_ui_context_alignment_pack_source_stays_out_of_fooddb_websearch_live_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_pl_ce_ui_context_alignment_pack.py"),
        Path("scripts/build_accurate_intake_pl_ce_ui_context_alignment_pack.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "from tavily",
        "import tavily",
        "tavilyclient",
        "tavilysearch",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "kimi",
        "grok",
        "live_llm_invoked = True",
        "web_tavily_used = True",
        "ready_for_live_diagnostic_decision = True",
        "ready_for_fdb_integration = True",
    ]
    combined_source = "\n".join(path.read_text(encoding="utf-8").lower() for path in source_paths)

    for fragment in forbidden:
        assert fragment.lower() not in combined_source


def test_ci_keeps_ui_context_alignment_pack_out_of_required_merge_path() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "product-pages-browser-e2e" in workflow
    assert "build_accurate_intake_product_pages_renderer_source_map.py" in workflow
    assert "build_accurate_intake_pl_ce_ui_context_alignment_pack.py" not in workflow
    assert "accurate_intake_pl_ce_ui_context_alignment_pack_ci.json" not in workflow
    assert "product_pages_renderer_source_map=artifacts/accurate_intake_product_pages_renderer_source_map_ci.json" not in workflow
    assert "accurate-intake-pl-ce-ui-context-alignment-pack-report" not in workflow
    assert not Path(".github/workflows/ci-advisory.yml").exists()
