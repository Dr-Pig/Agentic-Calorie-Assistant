from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any


REQUIRED_INPUTS = (
    "product_pages_renderer_source_map",
    "product_pages_browser_smoke",
    "product_pages_seven_day_diary_smoke",
    "product_pages_visual_qa",
)

EXPECTED_STATUSES = {
    "product_pages_renderer_source_map": "product_pages_renderer_source_map_ready_for_human_review",
    "product_pages_browser_smoke": "pass",
    "product_pages_seven_day_diary_smoke": "pass",
    "product_pages_visual_qa": "pass",
}

EXPECTED_ARTIFACT_TYPES = {
    "product_pages_renderer_source_map": "accurate_intake_product_pages_renderer_source_map",
    "product_pages_visual_qa": "accurate_intake_product_pages_visual_qa",
}

EXPECTED_SMOKE_IDS = {
    "product_pages_browser_smoke": "accurate_intake_product_pages_browser_smoke_v1",
    "product_pages_seven_day_diary_smoke": "accurate_intake_product_pages_seven_day_diary_smoke_v1",
}

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
    "mutation_authority",
    "frontend_semantic_owner",
    "frontend_selected_target",
    "deterministic_semantic_inference_used",
    "deterministic_selected_target",
    "raw_text_intent_router_used",
    "forbidden_storage_used",
)

REQUIRED_TRUE_FLAGS = {
    "product_pages_renderer_source_map": (
        "render_only_boundary_ok",
    ),
    "product_pages_browser_smoke": (
        "browser_executed",
        "chat_page_loaded",
        "chat_history_reloaded",
        "chat_scroll_behavior_checked",
        "today_page_loaded",
        "today_summary_rendered",
        "today_meal_list_rendered",
        "body_page_loaded",
        "body_plan_readback_checked",
        "body_plan_read_model_fields_rendered",
        "body_latest_weight_rendered_from_backend",
        "body_manual_target_read_model_rendered",
        "body_deficit_summary_rendered",
        "body_weekly_progress_rendered",
        "body_effective_budget_rendered",
        "today_body_cross_page_same_truth_checked",
        "desktop_no_overflow",
        "mobile_no_overflow",
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
}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {
            "",
            "0",
            "false",
            "no",
            "none",
            "null",
            "not_available",
            "not_checked",
        }
    return True


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
    if payload.get("blockers") not in (None, []):
        blockers.append(f"{group_id}.upstream_blockers_present")
    return blockers


def _claim_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
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


def _browser_value_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    today_values = _object_dict(payload.get("today_read_model_values"))
    body_values = _object_dict(payload.get("body_plan_read_model_values"))
    expected_today_values = {
        "target": "1550",
        "consumed": "400",
        "remaining": "1150",
    }
    expected_body_values = {
        "deficit_active_target": "1550 kcal",
        "deficit_consumed": "400 kcal",
        "deficit_remaining": "1150 kcal",
        "deficit_latest_weight": "70.4 kg",
        "effective_budget": "1550 kcal",
    }
    if not today_values:
        blockers.append("product_pages_browser_smoke.today_read_model_values_missing")
    if not body_values:
        blockers.append("product_pages_browser_smoke.body_read_model_values_missing")
    for field, expected_value in expected_today_values.items():
        if today_values and today_values.get(field) != expected_value:
            blockers.append(f"product_pages_browser_smoke.today_read_model_value_mismatch:{field}")
    for field, expected_value in expected_body_values.items():
        if body_values and body_values.get(field) != expected_value:
            blockers.append(f"product_pages_browser_smoke.body_read_model_value_mismatch:{field}")
    cross_page_pairs = {
        "target": ("target", "deficit_active_target"),
        "consumed": ("consumed", "deficit_consumed"),
        "remaining": ("remaining", "deficit_remaining"),
    }
    for field, (today_field, body_field) in cross_page_pairs.items():
        if today_values and body_values:
            body_value = str(body_values.get(body_field) or "").removesuffix(" kcal")
            if str(today_values.get(today_field) or "") != body_value:
                blockers.append(f"product_pages_browser_smoke.today_body_cross_page_same_truth_mismatch:{field}")
    if today_values and body_values:
        effective_budget = str(body_values.get("effective_budget") or "").removesuffix(" kcal")
        if str(today_values.get("target") or "") != effective_budget:
            blockers.append("product_pages_browser_smoke.today_body_cross_page_same_truth_mismatch:effective_budget")
    return blockers


def _group_specific_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    if group_id == "product_pages_browser_smoke":
        return _browser_value_blockers(payload)
    if group_id == "product_pages_seven_day_diary_smoke" and _int_value(payload.get("day_count_checked")) < 7:
        return ["product_pages_seven_day_diary_smoke.seven_day_window_incomplete"]
    return []


def _artifact_statuses(payloads: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    for group_id, payload in payloads.items():
        statuses[group_id] = {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "smoke_id": payload.get("smoke_id") or "not_available",
            "status": _status(payload),
            "browser_executed": payload.get("browser_executed", "not_applicable"),
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
    return statuses


def build_product_pages_ui_review_bundle_artifact(
    input_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inputs = {
        group_id: _object_dict(input_artifacts.get(group_id))
        for group_id in REQUIRED_INPUTS
    }
    blockers: list[str] = []
    for group_id, payload in inputs.items():
        blockers.extend(_identity_blockers(group_id, payload))
        blockers.extend(_claim_blockers(group_id, payload))
        blockers.extend(_required_true_blockers(group_id, payload))
        blockers.extend(_group_specific_blockers(group_id, payload))

    source_map_summary = _object_dict(inputs["product_pages_renderer_source_map"].get("summary"))
    browser_smoke = inputs["product_pages_browser_smoke"]
    today_values = _object_dict(browser_smoke.get("today_read_model_values"))
    body_values = _object_dict(browser_smoke.get("body_plan_read_model_values"))
    status = "product_pages_ui_review_ready_for_human_review" if not blockers else "blocked"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_product_pages_ui_review_bundle",
            "status": status,
            "claim_scope": "product_pages_ui_review_for_human_review_only",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "required_inputs": list(REQUIRED_INPUTS),
            "blockers": blockers,
            "included_artifact_statuses": _artifact_statuses(inputs),
            "summary": {
                "pages_verified": ["chat", "today", "body"],
                "renderer_source_map_page_count": _int_value(source_map_summary.get("page_count")),
                "renderer_source_map_selector_count": _int_value(source_map_summary.get("selector_count")),
                "renderer_source_map_endpoint_count": _int_value(source_map_summary.get("endpoint_count")),
                "renderer_source_map_backend_field_count": _int_value(
                    source_map_summary.get("backend_field_count")
                ),
                "browser_cross_page_same_truth_checked": (
                    browser_smoke.get("today_body_cross_page_same_truth_checked") is True
                ),
                "visual_qa_checked": inputs["product_pages_visual_qa"].get("status") == "pass",
                "today_values": today_values,
                "body_budget_values": {
                    "deficit_active_target": body_values.get("deficit_active_target") or "not_available",
                    "deficit_consumed": body_values.get("deficit_consumed") or "not_available",
                    "deficit_remaining": body_values.get("deficit_remaining") or "not_available",
                    "deficit_latest_weight": body_values.get("deficit_latest_weight") or "not_available",
                    "effective_budget": body_values.get("effective_budget") or "not_available",
                },
            },
            "review_checkpoints": [
                "chat_page_is_long_session_scrollable_without_trace_panel",
                "today_page_is_daily_diary_without_debug_surface",
                "body_page_renders_backend_bodybudget_read_models",
                "today_and_body_show_same_backend_budget_values_after_body_update",
                "desktop_and_mobile_visual_qa_have_no_overflow",
            ],
            "local_only": True,
            "diagnostic_only": True,
            "aggregate_only": True,
            "render_only_boundary_ok": not blockers,
            "human_review_required": True,
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
            "frontend_semantic_owner": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
        }
    )


__all__ = [
    "REQUIRED_INPUTS",
    "build_product_pages_ui_review_bundle_artifact",
]
