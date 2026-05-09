from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_current_shell_claim_boundary import build_current_shell_appshell_claim_boundary_fields
from app.composition.current_shell_browser_activation_contract import (
    REQUIRED_TRUE_FLAGS as BROWSER_ACTIVATION_REQUIRED_TRUE_FLAGS,
)
from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE,
    LEGACY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPES,
    set_legacy_alias_metadata,
)

REQUIRED_INPUTS = (
    "ui_same_truth_contract",
    "today_macro_runtime_mirror_gate",
    "product_pages_renderer_source_map",
    "product_pages_renderer_source_closure_gate",
    "product_pages_browser_smoke",
    "product_pages_seven_day_diary_smoke",
    "product_pages_body_noplan_degraded_smoke",
    "product_pages_short_term_context_smoke",
    "product_pages_target_candidate_ui_smoke",
    "product_pages_context_target_browser_closure",
    "product_pages_visual_qa",
    "fixture_full_product_loop_e2e",
)

EXPECTED_STATUSES = {
    "ui_same_truth_contract": "pass",
    "today_macro_runtime_mirror_gate": "today_macro_runtime_mirror_gate_ready_for_browser",
    "product_pages_renderer_source_map": "product_pages_renderer_source_map_ready_for_human_review",
    "product_pages_renderer_source_closure_gate": "product_pages_renderer_source_closure_ready_for_browser",
    "product_pages_browser_smoke": "pass",
    "product_pages_seven_day_diary_smoke": "pass",
    "product_pages_body_noplan_degraded_smoke": "pass",
    "product_pages_short_term_context_smoke": "pass",
    "product_pages_target_candidate_ui_smoke": "pass",
    "product_pages_context_target_browser_closure": "context_target_browser_closure_ready_for_self_use_flow_gate",
    "product_pages_visual_qa": "pass",
    "fixture_full_product_loop_e2e": "fixture_product_loop_e2e_diagnostic_pass",
}

EXPECTED_ARTIFACT_TYPES = {
    "ui_same_truth_contract": "accurate_intake_ui_same_truth_render_contract",
    "today_macro_runtime_mirror_gate": "accurate_intake_today_macro_runtime_mirror_gate",
    "product_pages_renderer_source_map": "accurate_intake_product_pages_renderer_source_map",
    "product_pages_renderer_source_closure_gate": "accurate_intake_product_pages_renderer_source_closure_gate",
    "product_pages_context_target_browser_closure": "accurate_intake_product_pages_context_target_browser_closure",
    "product_pages_visual_qa": "accurate_intake_product_pages_visual_qa",
    "fixture_full_product_loop_e2e": "accurate_intake_fixture_full_product_loop_e2e",
}

EXPECTED_PASS_TYPES = {
    "today_macro_runtime_mirror_gate": "runtime_backed",
    "product_pages_renderer_source_closure_gate": "contract",
    "product_pages_context_target_browser_closure": "browser_executed",
}

EXPECTED_SMOKE_IDS = {
    "product_pages_browser_smoke": "accurate_intake_product_pages_browser_smoke_v1",
    "product_pages_seven_day_diary_smoke": "accurate_intake_product_pages_seven_day_diary_smoke_v1",
    "product_pages_body_noplan_degraded_smoke": "accurate_intake_product_pages_body_noplan_degraded_smoke_v1",
    "product_pages_short_term_context_smoke": "accurate_intake_product_pages_short_term_context_smoke_v1",
    "product_pages_target_candidate_ui_smoke": "accurate_intake_product_pages_target_candidate_ui_smoke_v1",
}

BROWSER_INPUTS = (
    "product_pages_browser_smoke",
    "product_pages_seven_day_diary_smoke",
    "product_pages_body_noplan_degraded_smoke",
    "product_pages_short_term_context_smoke",
    "product_pages_target_candidate_ui_smoke",
    "product_pages_context_target_browser_closure",
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
    "mutation_authority",
    "frontend_semantic_owner",
    "frontend_selected_target",
    "frontend_selects_target",
    "frontend_macro_math_used",
    "assistant_text_macro_parsed",
    "deterministic_semantic_inference_used",
    "deterministic_selected_target",
    "raw_text_intent_router_used",
    "forbidden_storage_used",
)

REQUIRED_TRUE_FLAGS = {
    "ui_same_truth_contract": (
        "frontend_render_only",
    ),
    "today_macro_runtime_mirror_gate": (
        "macro_visible_case_checked",
        "macro_guarded_case_checked",
        "backend_macro_fields_required",
        "show_macro_false_suppresses_macro",
    ),
    "product_pages_renderer_source_map": (
        "render_only_boundary_ok",
    ),
    "product_pages_renderer_source_closure_gate": (
        "route_table_checked",
    ),
    "product_pages_browser_smoke": BROWSER_ACTIVATION_REQUIRED_TRUE_FLAGS["product_pages_browser_smoke"],
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
    "product_pages_body_noplan_degraded_smoke": (
        "browser_executed",
        "body_page_loaded",
        "today_page_loaded",
        "no_plan_body_status_rendered",
        "body_targets_hidden_for_no_plan",
        "body_budget_degraded_rendered",
        "today_no_plan_budget_rendered",
        "no_bootstrap_or_mutation_post",
        "product_pages_no_debug_trace",
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
    "product_pages_context_target_browser_closure": (
        "browser_executed",
        "context_engineering_present",
        "session_state_injected",
        "pending_meal_or_correction_context_present",
        "target_candidate_list_read_only",
        "context_strip_read_only",
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


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


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
    expected_pass_type = EXPECTED_PASS_TYPES.get(group_id)
    if expected_pass_type and payload.get("pass_type") != expected_pass_type:
        blockers.append(f"{group_id}.unexpected_pass_type:{payload.get('pass_type')}")
    expected_smoke_id = EXPECTED_SMOKE_IDS.get(group_id)
    if expected_smoke_id and payload.get("smoke_id") != expected_smoke_id:
        blockers.append(f"{group_id}.unexpected_smoke_id:{payload.get('smoke_id')}")
    if payload.get("blockers") not in (None, []):
        blockers.append(f"{group_id}.upstream_blockers_present")
    return blockers


def _required_true_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for flag in REQUIRED_TRUE_FLAGS.get(group_id, ()):
        if payload.get(flag) is not True:
            suffix = "browser_not_executed" if flag == "browser_executed" else f"{flag}_not_true"
            blockers.append(f"{group_id}.{suffix}")
    return blockers


def _forbidden_claim_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"{group_id}.{flag}"
        for flag in FORBIDDEN_TRUTHY_FLAGS
        if _claim_is_true(payload.get(flag))
    ]


def _group_specific_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if group_id == "product_pages_renderer_source_map":
        summary = _object_dict(payload.get("summary"))
        if _int_value(summary.get("page_count")) != 3:
            blockers.append("product_pages_renderer_source_map.page_count_mismatch")
        if _int_value(summary.get("selector_count")) < 30:
            blockers.append("product_pages_renderer_source_map.selector_count_too_low")
        if _int_value(summary.get("endpoint_count")) < 7:
            blockers.append("product_pages_renderer_source_map.endpoint_count_too_low")
    if group_id == "product_pages_renderer_source_closure_gate":
        summary = _object_dict(payload.get("summary"))
        if _int_value(summary.get("page_count")) != 3:
            blockers.append("product_pages_renderer_source_closure_gate.page_count_mismatch")
        if _int_value(summary.get("endpoint_method_contract_count")) < 7:
            blockers.append(
                "product_pages_renderer_source_closure_gate.endpoint_method_contract_count_too_low"
            )
    if group_id == "product_pages_seven_day_diary_smoke":
        if _int_value(payload.get("day_count_checked")) < 7:
            blockers.append("product_pages_seven_day_diary_smoke.seven_day_window_incomplete")
        if _int_value(payload.get("manager_provider_call_count")) != 0:
            blockers.append("product_pages_seven_day_diary_smoke.manager_provider_called")
    if group_id == "product_pages_body_noplan_degraded_smoke":
        body_values = _object_dict(payload.get("body_values"))
        today_values = _object_dict(payload.get("today_values"))
        for field in ("daily_target", "tdee", "active_target", "remaining"):
            if str(body_values.get(field) or "") != "--":
                blockers.append(f"product_pages_body_noplan_degraded_smoke.body_{field}_not_hidden")
        for field in ("budget", "consumed", "remaining"):
            if str(today_values.get(field) or "") != "0":
                blockers.append(f"product_pages_body_noplan_degraded_smoke.today_{field}_not_zero")
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
    if group_id == "product_pages_context_target_browser_closure":
        if _int_value(payload.get("target_candidate_count_rendered")) < 1:
            blockers.append(
                "product_pages_context_target_browser_closure.target_candidate_count_missing"
            )
        if not _list_value(payload.get("target_candidate_names_rendered")):
            blockers.append(
                "product_pages_context_target_browser_closure.target_candidate_names_missing"
            )
    if group_id == "fixture_full_product_loop_e2e":
        completed_steps = {str(item) for item in _list_value(payload.get("completed_product_loop_steps"))}
        for required_step in REQUIRED_PRODUCT_LOOP_STEPS:
            if required_step not in completed_steps:
                blockers.append(f"fixture_full_product_loop_e2e.completed_step_missing:{required_step}")
    return blockers


def _artifact_statuses(inputs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        group_id: {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "smoke_id": payload.get("smoke_id") or "not_available",
            "status": _status(payload),
            "browser_executed": payload.get("browser_executed", "not_applicable"),
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
        for group_id, payload in inputs.items()
    }


def _strongest_consumed_pass_type(inputs: dict[str, dict[str, Any]]) -> str:
    ranking = {
        "static": 0,
        "contract": 1,
        "fixture": 2,
        "runtime_backed": 3,
        "browser_executed": 4,
    }
    strongest = "contract"
    for payload in inputs.values():
        pass_type = str(payload.get("pass_type") or "")
        if ranking.get(pass_type, -1) > ranking[strongest]:
            strongest = pass_type
    if any(inputs[group_id].get("browser_executed") is True for group_id in BROWSER_INPUTS):
        return "browser_executed"
    return strongest


def build_pl_ce_product_pages_self_use_flow_gate_artifact(
    input_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inputs = {
        group_id: _object_dict(input_artifacts.get(group_id))
        for group_id in REQUIRED_INPUTS
    }
    blockers: list[str] = []
    for group_id, payload in inputs.items():
        blockers.extend(_identity_blockers(group_id, payload))
        blockers.extend(_required_true_blockers(group_id, payload))
        blockers.extend(_forbidden_claim_blockers(group_id, payload))
        blockers.extend(_group_specific_blockers(group_id, payload))

    all_browser_executed = all(inputs[group_id].get("browser_executed") is True for group_id in BROWSER_INPUTS)
    renderer_summary = _object_dict(inputs["product_pages_renderer_source_map"].get("summary"))
    closure_summary = _object_dict(inputs["product_pages_renderer_source_closure_gate"].get("summary"))
    completed_steps = _list_value(inputs["fixture_full_product_loop_e2e"].get("completed_product_loop_steps"))
    status = "product_pages_self_use_flow_ready_for_human_review" if not blockers else "blocked"
    payload = {
            "artifact_schema_version": "1.0",
            "artifact_type": CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE,
            "status": status,
            "claim_scope": "local_product_pages_self_use_flow_diagnostic_for_human_review_only",
            **build_current_shell_appshell_claim_boundary_fields(),
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "required_inputs": list(REQUIRED_INPUTS),
            "browser_required_inputs": list(BROWSER_INPUTS),
            "browser_executed_required": True,
            "blocked_browser_is_not_pass": True,
            "all_required_browser_artifacts_executed": all_browser_executed,
            "blockers": blockers,
            "included_artifact_statuses": _artifact_statuses(inputs),
            "summary": {
                "pages_verified": ["chat", "today", "body"],
                "three_distinct_pages_verified": inputs["product_pages_visual_qa"].get("three_distinct_pages_verified") is True,
                "renderer_source_map_page_count": _int_value(renderer_summary.get("page_count")),
                "renderer_source_map_selector_count": _int_value(renderer_summary.get("selector_count")),
                "renderer_source_map_endpoint_count": _int_value(renderer_summary.get("endpoint_count")),
                "renderer_source_closure_checked": (
                    inputs["product_pages_renderer_source_closure_gate"].get("route_table_checked") is True
                    and inputs["product_pages_renderer_source_closure_gate"].get("status")
                    == EXPECTED_STATUSES["product_pages_renderer_source_closure_gate"]
                ),
                "renderer_source_closure_endpoint_contract_count": _int_value(
                    closure_summary.get("endpoint_method_contract_count")
                ),
                "seven_day_diary_checked": inputs["product_pages_seven_day_diary_smoke"].get("seven_day_window_checked") is True,
                "body_noplan_degraded_checked": (
                    inputs["product_pages_body_noplan_degraded_smoke"].get("status")
                    == EXPECTED_STATUSES["product_pages_body_noplan_degraded_smoke"]
                    and inputs["product_pages_body_noplan_degraded_smoke"].get("browser_executed") is True
                ),
                "short_term_context_checked": inputs["product_pages_short_term_context_smoke"].get("chat_history_context_fields_reloaded") is True,
                "target_candidate_ui_checked": inputs["product_pages_target_candidate_ui_smoke"].get("target_candidate_surface_checked") is True,
                "context_target_browser_closure_checked": (
                    inputs["product_pages_context_target_browser_closure"].get("context_engineering_present")
                    is True
                    and inputs["product_pages_context_target_browser_closure"].get("status")
                    == EXPECTED_STATUSES["product_pages_context_target_browser_closure"]
                ),
                "today_macro_runtime_mirror_checked": (
                    inputs["today_macro_runtime_mirror_gate"].get("status")
                    == EXPECTED_STATUSES["today_macro_runtime_mirror_gate"]
                    and inputs["today_macro_runtime_mirror_gate"].get("macro_visible_case_checked") is True
                    and inputs["today_macro_runtime_mirror_gate"].get("macro_guarded_case_checked") is True
                ),
                "fixture_product_loop_steps_checked": len(completed_steps),
                "strongest_consumed_pass_type": _strongest_consumed_pass_type(inputs),
            },
            "human_review_required": True,
            "review_required_before_provider_call": True,
            "frontend_render_only": inputs["ui_same_truth_contract"].get("frontend_render_only") is True,
            "frontend_semantic_owner": False,
            "fixture_evidence_used": True,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "production_db_used": False,
            "manager_context_packet_schema_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
        }
    set_legacy_alias_metadata(payload, legacy_artifact_types=LEGACY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPES)
    return _json_safe(payload)


__all__ = [
    "REQUIRED_INPUTS",
    "build_pl_ce_product_pages_self_use_flow_gate_artifact",
]
