from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any


REQUIRED_INPUTS = (
    "pl_ce_local_mvp_candidate_bundle",
    "product_pages_browser_smoke",
    "product_pages_seven_day_diary_smoke",
    "product_pages_short_term_context_smoke",
    "product_pages_target_candidate_ui_smoke",
    "product_pages_visual_qa",
    "fixture_full_product_loop_e2e",
)

EXPECTED_STATUSES = {
    "pl_ce_local_mvp_candidate_bundle": "pl_ce_local_mvp_candidate_ready_for_human_review",
    "product_pages_browser_smoke": "pass",
    "product_pages_seven_day_diary_smoke": "pass",
    "product_pages_short_term_context_smoke": "pass",
    "product_pages_target_candidate_ui_smoke": "pass",
    "product_pages_visual_qa": "pass",
    "fixture_full_product_loop_e2e": "fixture_product_loop_e2e_diagnostic_pass",
}

EXPECTED_ARTIFACT_TYPES = {
    "pl_ce_local_mvp_candidate_bundle": "accurate_intake_pl_ce_local_mvp_candidate_bundle",
    "product_pages_visual_qa": "accurate_intake_product_pages_visual_qa",
    "fixture_full_product_loop_e2e": "accurate_intake_fixture_full_product_loop_e2e",
}

EXPECTED_SMOKE_IDS = {
    "product_pages_browser_smoke": "accurate_intake_product_pages_browser_smoke_v1",
    "product_pages_seven_day_diary_smoke": "accurate_intake_product_pages_seven_day_diary_smoke_v1",
    "product_pages_short_term_context_smoke": "accurate_intake_product_pages_short_term_context_smoke_v1",
    "product_pages_target_candidate_ui_smoke": "accurate_intake_product_pages_target_candidate_ui_smoke_v1",
}

BROWSER_ARTIFACTS = (
    "product_pages_browser_smoke",
    "product_pages_seven_day_diary_smoke",
    "product_pages_short_term_context_smoke",
    "product_pages_target_candidate_ui_smoke",
    "product_pages_visual_qa",
)

REQUIRED_PRODUCT_LOOP_STEPS = (
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
)

FORBIDDEN_TRUTHY_FLAGS = (
    "ready_for_live_diagnostic_decision",
    "ready_for_fdb_integration",
    "live_llm_invoked",
    "live_provider_called",
    "web_tavily_used",
    "web_tavily_invoked",
    "websearch_evidence_used",
    "fooddb_evidence_used",
    "fooddb_truth_updated",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_db_used",
    "manager_context_packet_schema_changed",
    "runtime_truth_changed",
    "mutation_changed",
    "frontend_semantic_owner",
    "frontend_selected_target",
    "deterministic_semantic_inference_used",
    "deterministic_selected_target",
    "raw_text_intent_router_used",
    "mutation_authority",
    "forbidden_storage_used",
)

REQUIRED_TRUE_FLAGS = {
    "product_pages_browser_smoke": (
        "browser_executed",
        "chat_page_loaded",
        "chat_sent_cjk_message",
        "chat_assistant_bubble_rendered",
        "chat_history_reloaded",
        "chat_scroll_behavior_checked",
        "chat_reload_scroll_behavior_checked",
        "today_page_loaded",
        "today_date_switch_checked",
        "today_summary_rendered",
        "today_meal_list_rendered",
        "body_page_loaded",
        "body_active_plan_rendered",
        "body_plan_readback_checked",
        "body_plan_read_model_fields_rendered",
        "body_latest_weight_rendered_from_backend",
        "body_manual_target_read_model_rendered",
        "today_manual_target_readback_checked",
        "desktop_no_overflow",
        "mobile_no_overflow",
        "mobile_populated_state_checked",
        "product_cjk_copy_rendered",
        "nav_session_query_preserved",
    ),
    "product_pages_seven_day_diary_smoke": (
        "browser_executed",
        "seven_day_window_checked",
        "per_day_diary_isolated",
        "per_day_budget_values_checked",
        "today_date_strip_checked",
        "today_nav_date_preserved",
        "today_chat_link_date_preserved",
        "desktop_no_overflow",
        "mobile_no_overflow",
    ),
    "product_pages_short_term_context_smoke": (
        "browser_executed",
        "browser_reload_checked",
        "fixture_manager_used",
        "pending_followup_created",
        "pending_followup_reloaded",
        "context_policy_version_present",
        "loaded_context_summary_present",
        "omitted_context_summary_present",
        "pending_pins_present_after_followup",
        "chat_history_context_fields_reloaded",
        "chat_cjk_roundtrip_rendered",
        "assistant_followup_bubble_rendered",
        "assistant_commit_bubble_rendered",
        "today_same_day_meal_rendered",
        "today_summary_rendered",
        "product_pages_no_debug_trace",
    ),
    "product_pages_target_candidate_ui_smoke": (
        "browser_executed",
        "browser_reload_checked",
        "chat_page_loaded",
        "chat_history_reloaded",
        "target_candidate_surface_checked",
        "target_candidate_list_read_only",
        "context_strip_read_only",
        "product_pages_no_debug_trace",
    ),
    "product_pages_visual_qa": (
        "browser_executed",
        "desktop_screenshots_captured",
        "mobile_screenshots_captured",
        "chat_surface_verified",
        "today_surface_verified",
        "body_surface_verified",
        "three_distinct_pages_verified",
        "desktop_no_overflow",
        "mobile_no_overflow",
        "visible_trace_debug_terms_absent",
    ),
    "fixture_full_product_loop_e2e": (
        "fixture_evidence_used",
    ),
}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _expected_weight_history_value(payload: dict[str, Any]) -> str:
    local_date = payload.get("local_date")
    if isinstance(local_date, str) and local_date:
        return f"{local_date} | 70.4 kg"
    return "2026-05-05 | 70.4 kg"


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "claimed", "enabled"}
    return False


def _identity_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _status(payload) != EXPECTED_STATUSES[group_id]:
        blockers.append(f"{group_id}.unexpected_status:{_status(payload)}")
    expected_type = EXPECTED_ARTIFACT_TYPES.get(group_id)
    if expected_type and payload.get("artifact_type") != expected_type:
        blockers.append(f"{group_id}.unexpected_artifact_type:{payload.get('artifact_type')}")
    expected_smoke_id = EXPECTED_SMOKE_IDS.get(group_id)
    if expected_smoke_id and payload.get("smoke_id") != expected_smoke_id:
        blockers.append(f"{group_id}.unexpected_smoke_id:{payload.get('smoke_id')}")
    return blockers


def _forbidden_claim_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"{group_id}.{flag}"
        for flag in FORBIDDEN_TRUTHY_FLAGS
        if _claim_is_true(payload.get(flag))
    ]


def _required_true_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for flag in REQUIRED_TRUE_FLAGS.get(group_id, ()):
        if payload.get(flag) is not True:
            suffix = "browser_not_executed" if flag == "browser_executed" else f"{flag}_not_true"
            blockers.append(f"{group_id}.{suffix}")
    return blockers


def _group_specific_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if group_id == "pl_ce_local_mvp_candidate_bundle":
        if payload.get("activation_gate_status") != "blocked_pending_human_and_browser_activation":
            blockers.append("pl_ce_local_mvp_candidate_bundle.unexpected_activation_gate_status")
    if group_id == "product_pages_browser_smoke":
        body_values = _object_dict(payload.get("body_plan_read_model_values"))
        if not body_values:
            blockers.append("product_pages_browser_smoke.body_read_model_values_missing")
        expected_body_values = {
            "daily_target": "1550 kcal",
            "tdee": "1819 kcal",
            "current_weight": "70 kg",
            "target_weight": "65 kg",
            "activity": "light",
            "goal": "Lose weight",
        }
        for field, expected_value in expected_body_values.items():
            if body_values and body_values.get(field) != expected_value:
                blockers.append(f"product_pages_browser_smoke.body_read_model_value_mismatch:{field}")
        if body_values and _expected_weight_history_value(payload) not in str(
            body_values.get("weight_history") or ""
        ):
            blockers.append("product_pages_browser_smoke.body_read_model_value_mismatch:weight_history")
    if group_id == "product_pages_seven_day_diary_smoke":
        if _int_value(payload.get("day_count_checked")) < 7:
            blockers.append("product_pages_seven_day_diary_smoke.seven_day_window_incomplete")
        if _int_value(payload.get("manager_provider_call_count")) != 0:
            blockers.append("product_pages_seven_day_diary_smoke.manager_provider_called")
    if group_id == "product_pages_target_candidate_ui_smoke":
        if _int_value(payload.get("target_candidate_count_rendered")) < 2:
            blockers.append("product_pages_target_candidate_ui_smoke.target_candidate_count_too_low")
        rendered = [str(item) for item in _list_value(payload.get("target_candidate_names_rendered"))]
        for required_name in ("luwei", "milk tea"):
            if required_name not in rendered:
                blockers.append(
                    f"product_pages_target_candidate_ui_smoke.target_candidate_missing:{required_name}"
                )
        if _int_value(payload.get("manager_provider_call_count")) != 0:
            blockers.append("product_pages_target_candidate_ui_smoke.manager_provider_called")
    if group_id == "fixture_full_product_loop_e2e":
        completed_steps = {str(item) for item in _list_value(payload.get("completed_product_loop_steps"))}
        for required_step in REQUIRED_PRODUCT_LOOP_STEPS:
            if required_step not in completed_steps:
                blockers.append(f"fixture_full_product_loop_e2e.completed_step_missing:{required_step}")
    return blockers


def _artifact_statuses(payloads: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        group_id: {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "smoke_id": payload.get("smoke_id") or "not_available",
            "status": _status(payload),
            "browser_executed": payload.get("browser_executed", "not_applicable"),
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
        for group_id, payload in payloads.items()
    }


def build_pl_ce_browser_activation_evidence_gate_artifact(
    input_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inputs = {
        group_id: _object_dict(input_artifacts.get(group_id))
        for group_id in REQUIRED_INPUTS
    }
    blockers: list[str] = []
    for group_id, payload in inputs.items():
        blockers.extend(_identity_blockers(group_id, payload))
        blockers.extend(_forbidden_claim_blockers(group_id, payload))
        blockers.extend(_required_true_blockers(group_id, payload))
        blockers.extend(_group_specific_blockers(group_id, payload))

    all_browser_executed = all(
        inputs[group_id].get("browser_executed") is True for group_id in BROWSER_ARTIFACTS
    )
    status = "browser_activation_evidence_ready_for_human_review" if not blockers else "blocked"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_browser_activation_evidence_gate",
            "status": status,
            "claim_scope": "pl_ce_browser_activation_evidence_for_human_review_only",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "required_inputs": list(REQUIRED_INPUTS),
            "browser_required_inputs": list(BROWSER_ARTIFACTS),
            "blockers": blockers,
            "included_artifact_statuses": _artifact_statuses(inputs),
            "browser_executed_required": True,
            "all_required_browser_artifacts_executed": all_browser_executed,
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "aggregate_only": True,
            "self_generated_evidence_used": False,
            "review_required_before_provider_call": True,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "shared_contract_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "live_provider_called": False,
            "web_tavily_used": False,
            "websearch_evidence_used": False,
            "fooddb_evidence_used": False,
            "fooddb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_db_used": False,
            "manager_context_packet_schema_changed": False,
            "mutation_authority": False,
            "summary": {
                "browser_artifact_count": len(BROWSER_ARTIFACTS),
                "browser_executed_count": sum(
                    1
                    for group_id in BROWSER_ARTIFACTS
                    if inputs[group_id].get("browser_executed") is True
                ),
                "requires_three_distinct_pages": True,
                "requires_seven_day_today_diary": True,
                "requires_short_term_context_render": True,
                "requires_target_candidate_ui": True,
                "requires_fixture_full_product_loop_e2e": True,
                "requires_visual_qa": True,
                "requires_no_debug_trace_leak": True,
                "fixture_product_loop_step_count": len(
                    _list_value(inputs["fixture_full_product_loop_e2e"].get("completed_product_loop_steps"))
                ),
            },
        }
    )


__all__ = [
    "BROWSER_ARTIFACTS",
    "EXPECTED_ARTIFACT_TYPES",
    "EXPECTED_SMOKE_IDS",
    "EXPECTED_STATUSES",
    "REQUIRED_INPUTS",
    "build_pl_ce_browser_activation_evidence_gate_artifact",
]
