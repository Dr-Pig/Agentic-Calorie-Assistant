from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_pl_ce_browser_activation_evidence_gate import (
    build_pl_ce_browser_activation_evidence_gate_artifact,
)


def _valid_inputs() -> dict[str, dict[str, object]]:
    return {
        "pl_ce_local_mvp_candidate_bundle": {
            "artifact_type": "accurate_intake_pl_ce_local_mvp_candidate_bundle",
            "status": "pl_ce_local_mvp_candidate_ready_for_human_review",
            "activation_gate_status": "blocked_pending_human_and_browser_activation",
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
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
            "today_manual_target_readback_checked": True,
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
    }


def test_browser_activation_gate_requires_real_browser_evidence_without_readiness_claims() -> None:
    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(_valid_inputs())

    assert artifact["artifact_type"] == "accurate_intake_pl_ce_browser_activation_evidence_gate"
    assert artifact["status"] == "browser_activation_evidence_ready_for_human_review"
    assert artifact["browser_executed_required"] is True
    assert artifact["all_required_browser_artifacts_executed"] is True
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["ready_for_fdb_integration"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["real_fooddb_pass_claimed"] is False
    assert artifact["dogfood_pass"] is False
    assert artifact["web_readiness_claimed"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["blockers"] == []


def test_browser_activation_gate_blocks_missing_or_blocked_browser_execution() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_browser_smoke"]["browser_executed"] = False
    inputs["product_pages_browser_smoke"]["status"] = "blocked"

    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_browser_smoke.unexpected_status:blocked" in artifact["blockers"]
    assert "product_pages_browser_smoke.browser_not_executed" in artifact["blockers"]
    assert artifact["all_required_browser_artifacts_executed"] is False
    assert artifact["ready_for_live_diagnostic_decision"] is False


def test_browser_activation_gate_blocks_swapped_identity_and_unknown_mvp_candidate() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_seven_day_diary_smoke"]["smoke_id"] = "accurate_intake_product_pages_browser_smoke_v1"
    inputs["pl_ce_local_mvp_candidate_bundle"]["artifact_type"] = "wrong"

    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_seven_day_diary_smoke.unexpected_smoke_id:accurate_intake_product_pages_browser_smoke_v1" in artifact["blockers"]
    assert "pl_ce_local_mvp_candidate_bundle.unexpected_artifact_type:wrong" in artifact["blockers"]


def test_browser_activation_gate_blocks_frontend_semantics_live_or_fooddb_claims() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_short_term_context_smoke"]["deterministic_semantic_inference_used"] = True
    inputs["product_pages_visual_qa"]["frontend_semantic_owner"] = True
    inputs["product_pages_browser_smoke"]["fooddb_evidence_used"] = True
    inputs["product_pages_seven_day_diary_smoke"]["manager_provider_call_count"] = 1

    artifact = build_pl_ce_browser_activation_evidence_gate_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_short_term_context_smoke.deterministic_semantic_inference_used" in artifact["blockers"]
    assert "product_pages_visual_qa.frontend_semantic_owner" in artifact["blockers"]
    assert "product_pages_browser_smoke.fooddb_evidence_used" in artifact["blockers"]
    assert "product_pages_seven_day_diary_smoke.manager_provider_called" in artifact["blockers"]


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
    from scripts.build_accurate_intake_pl_ce_browser_activation_evidence_gate import main

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
    from scripts.build_accurate_intake_pl_ce_browser_activation_evidence_gate import main

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


def test_ci_builds_browser_activation_evidence_gate() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "test_accurate_intake_pl_ce_browser_activation_evidence_gate.py" in workflow
    assert "run_accurate_intake_product_pages_short_term_context_smoke.py --require-browser-execution" in workflow
    assert "build_accurate_intake_pl_ce_browser_activation_evidence_gate.py" in workflow
    assert "accurate_intake_pl_ce_browser_activation_evidence_gate_ci.json" in workflow
