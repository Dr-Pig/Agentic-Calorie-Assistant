from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_product_pages_ui_review_bundle import (
    REQUIRED_INPUTS,
    build_product_pages_ui_review_bundle_artifact,
)


def _valid_inputs() -> dict[str, dict[str, object]]:
    return {
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
                "selector_count": 48,
                "endpoint_count": 11,
                "backend_field_count": 45,
            },
        },
        "product_pages_browser_smoke": {
            "smoke_id": "accurate_intake_product_pages_browser_smoke_v1",
            "status": "pass",
            "blockers": [],
            "browser_executed": True,
            "chat_page_loaded": True,
            "chat_history_reloaded": True,
            "chat_scroll_behavior_checked": True,
            "today_page_loaded": True,
            "today_summary_rendered": True,
            "today_meal_list_rendered": True,
            "body_page_loaded": True,
            "body_plan_readback_checked": True,
            "body_plan_read_model_fields_rendered": True,
            "body_latest_weight_rendered_from_backend": True,
            "body_manual_target_read_model_rendered": True,
            "body_deficit_summary_rendered": True,
            "body_weekly_progress_rendered": True,
            "body_effective_budget_rendered": True,
            "today_body_cross_page_same_truth_checked": True,
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
            "today_read_model_values": {
                "target": "1550",
                "consumed": "400",
                "remaining": "1150",
            },
            "body_plan_read_model_values": {
                "daily_target": "1550 kcal",
                "deficit_active_target": "1550 kcal",
                "deficit_consumed": "400 kcal",
                "deficit_remaining": "1150 kcal",
                "deficit_latest_weight": "70.4 kg",
                "effective_budget": "1550 kcal",
                "weight_history": "2026-05-05 | 70.4 kg",
            },
        },
        "product_pages_seven_day_diary_smoke": {
            "smoke_id": "accurate_intake_product_pages_seven_day_diary_smoke_v1",
            "status": "pass",
            "blockers": [],
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
        "product_pages_visual_qa": {
            "artifact_type": "accurate_intake_product_pages_visual_qa",
            "status": "pass",
            "blockers": [],
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
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
    }


def test_product_pages_ui_review_bundle_requires_renderer_browser_visual_and_same_truth() -> None:
    artifact = build_product_pages_ui_review_bundle_artifact(_valid_inputs())

    assert artifact["artifact_type"] == "accurate_intake_product_pages_ui_review_bundle"
    assert artifact["status"] == "product_pages_ui_review_ready_for_human_review"
    assert artifact["required_inputs"] == list(REQUIRED_INPUTS)
    assert artifact["blockers"] == []
    assert artifact["summary"]["pages_verified"] == ["chat", "today", "body"]
    assert artifact["summary"]["renderer_source_map_page_count"] == 3
    assert artifact["summary"]["browser_cross_page_same_truth_checked"] is True
    assert artifact["summary"]["visual_qa_checked"] is True
    assert artifact["summary"]["today_values"] == {"target": "1550", "consumed": "400", "remaining": "1150"}
    assert artifact["summary"]["body_budget_values"]["deficit_remaining"] == "1150 kcal"
    assert artifact["render_only_boundary_ok"] is True
    assert artifact["human_review_required"] is True
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["ready_for_fdb_integration"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False


def test_product_pages_ui_review_bundle_blocks_missing_cross_page_same_truth() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_browser_smoke"]["today_body_cross_page_same_truth_checked"] = False

    artifact = build_product_pages_ui_review_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_browser_smoke.today_body_cross_page_same_truth_checked_not_true" in artifact["blockers"]


def test_product_pages_ui_review_bundle_blocks_today_body_value_mismatch() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_browser_smoke"]["today_read_model_values"] = {
        "target": "1312",
        "consumed": "400",
        "remaining": "912",
    }

    artifact = build_product_pages_ui_review_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_browser_smoke.today_read_model_value_mismatch:target" in artifact["blockers"]
    assert "product_pages_browser_smoke.today_body_cross_page_same_truth_mismatch:target" in artifact["blockers"]
    assert "product_pages_browser_smoke.today_body_cross_page_same_truth_mismatch:remaining" in artifact["blockers"]


def test_product_pages_ui_review_bundle_blocks_visual_or_renderer_gaps() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_renderer_source_map"]["render_only_boundary_ok"] = False
    inputs["product_pages_visual_qa"]["mobile_no_overflow"] = False
    inputs["product_pages_visual_qa"]["visible_trace_debug_terms_absent"] = False

    artifact = build_product_pages_ui_review_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_renderer_source_map.render_only_boundary_ok_not_true" in artifact["blockers"]
    assert "product_pages_visual_qa.mobile_no_overflow_not_true" in artifact["blockers"]
    assert "product_pages_visual_qa.visible_trace_debug_terms_absent_not_true" in artifact["blockers"]


def test_product_pages_ui_review_bundle_blocks_frontend_or_live_truth_overclaims() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_browser_smoke"]["frontend_semantic_owner"] = True
    inputs["product_pages_visual_qa"]["product_readiness_claimed"] = True
    inputs["product_pages_browser_smoke"]["fooddb_evidence_used"] = True

    artifact = build_product_pages_ui_review_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_browser_smoke.frontend_semantic_owner" in artifact["blockers"]
    assert "product_pages_visual_qa.product_readiness_claimed" in artifact["blockers"]
    assert "product_pages_browser_smoke.fooddb_evidence_used" in artifact["blockers"]


def test_product_pages_ui_review_bundle_cli_writes_from_existing_artifacts(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_product_pages_ui_review_bundle import main

    output_path = tmp_path / "ui-review-bundle.json"
    args = ["--output", str(output_path)]
    for group_id, payload in _valid_inputs().items():
        artifact_path = tmp_path / f"{group_id}.json"
        artifact_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        args.extend(["--artifact", f"{group_id}={artifact_path}"])

    exit_code = main(args)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "product_pages_ui_review_ready_for_human_review"
    assert artifact["included_artifact_statuses"]["product_pages_visual_qa"]["source_artifact_path"]


def test_product_pages_ui_review_bundle_source_stays_out_of_fooddb_websearch_live_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_product_pages_ui_review_bundle.py"),
        Path("scripts/build_accurate_intake_product_pages_ui_review_bundle.py"),
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
