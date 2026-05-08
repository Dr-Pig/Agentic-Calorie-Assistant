from __future__ import annotations

from typing import Any

from app.composition.accurate_intake_pl_ce_activation_manifest_contract import (
    BROWSER_ARTIFACTS,
    CONTEXT_LIVE_REQUIRED_CASE_IDS,
)
from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID,
)


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _list_contains_all(value: Any, expected_values: tuple[str, ...]) -> bool:
    if not isinstance(value, list):
        return False
    return set(expected_values).issubset(set(str(item) for item in value))


def local_mvp_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("activation_gate_status") != "blocked_pending_human_and_browser_activation":
        blockers.append(
            f"{CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID}.unexpected_activation_gate_status"
        )
    fooddb_dependency = _object_dict(payload.get("fooddb_dependency"))
    if fooddb_dependency.get("fooddb_artifact_status") != "blocked_waiting_for_fdb_artifact":
        blockers.append(
            f"{CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID}.fooddb_stop_gate_missing"
        )
    if fooddb_dependency.get("ready_for_fdb_integration") is not False:
        blockers.append(
            f"{CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID}.fooddb_integration_not_blocked"
        )
    activation_policy = _object_dict(_object_dict(payload.get("browser_gate_policy")).get("activation_gate"))
    if activation_policy.get("require_browser_execution") is not True:
        blockers.append(
            f"{CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID}.activation_browser_not_required"
        )
    if activation_policy.get("browser_executed_required") is not True:
        blockers.append(
            f"{CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID}.activation_browser_execution_not_required"
        )
    return blockers


def browser_gate_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _object_dict(payload.get("summary"))
    if payload.get("all_required_browser_artifacts_executed") is not True:
        blockers.append("pl_ce_browser_activation_evidence_gate.browser_artifacts_not_all_executed")
    if payload.get("browser_executed_required") is not True:
        blockers.append("pl_ce_browser_activation_evidence_gate.browser_not_required")
    if not _list_contains_all(payload.get("browser_required_inputs"), tuple(BROWSER_ARTIFACTS)):
        blockers.append("pl_ce_browser_activation_evidence_gate.browser_inputs_incomplete")
    if summary.get("browser_artifact_count") != len(BROWSER_ARTIFACTS):
        blockers.append("pl_ce_browser_activation_evidence_gate.browser_artifact_count_mismatch")
    if summary.get("browser_executed_count") != len(BROWSER_ARTIFACTS):
        blockers.append("pl_ce_browser_activation_evidence_gate.browser_executed_count_mismatch")
    for flag in (
        "requires_three_distinct_pages",
        "requires_seven_day_today_diary",
        "requires_short_term_context_render",
        "requires_target_candidate_ui",
        "requires_body_noplan_degraded_browser",
        "requires_fixture_full_product_loop_e2e",
        "requires_product_pages_self_use_flow_gate",
        "requires_visual_qa",
        "requires_no_debug_trace_leak",
    ):
        if summary.get(flag) is not True:
            blockers.append(f"pl_ce_browser_activation_evidence_gate.{flag}_not_true")
    if summary.get("self_use_flow_gate_checked") is not True:
        blockers.append("pl_ce_browser_activation_evidence_gate.self_use_flow_gate_not_checked")
    if summary.get("self_use_flow_gate_strongest_pass_type") != "browser_executed":
        blockers.append("pl_ce_browser_activation_evidence_gate.self_use_flow_gate_not_browser_executed")
    if _int_value(summary.get("fixture_product_loop_step_count")) < 10:
        blockers.append("pl_ce_browser_activation_evidence_gate.fixture_product_loop_step_count_too_low")
    return blockers


def ui_context_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _object_dict(payload.get("summary"))
    if summary.get("pages_verified") != ["chat", "today", "body"]:
        blockers.append("pl_ce_ui_context_alignment_pack.pages_verified_mismatch")
    for flag, suffix in (
        ("seven_day_diary_checked", "seven_day_diary_not_checked"),
        ("chat_context_reload_checked", "chat_context_reload_not_checked"),
        ("body_read_model_checked", "body_read_model_not_checked"),
    ):
        if summary.get(flag) is not True:
            blockers.append(f"pl_ce_ui_context_alignment_pack.{suffix}")
    if _int_value(summary.get("context_covered_capabilities")) < 9:
        blockers.append("pl_ce_ui_context_alignment_pack.context_capabilities_not_covered")
    if summary.get("renderer_source_map_page_count") != 3:
        blockers.append("pl_ce_ui_context_alignment_pack.renderer_source_map_page_count_mismatch")
    if _int_value(summary.get("renderer_source_map_selector_count")) < 30:
        blockers.append("pl_ce_ui_context_alignment_pack.renderer_source_map_selector_count_too_low")
    if _int_value(summary.get("renderer_source_map_endpoint_count")) < 7:
        blockers.append("pl_ce_ui_context_alignment_pack.renderer_source_map_endpoint_count_too_low")
    return blockers


def context_dry_run_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _object_dict(payload.get("summary"))
    for flag in ("diagnostic_only", "fixture_only", "plan_only"):
        if payload.get(flag) is not True:
            blockers.append(f"{group_id}.{flag}_not_true")
    if group_id == "context_live_diagnostic_dry_run_evaluator":
        if payload.get("fixed_case_matrix_used") is not True:
            blockers.append(f"{group_id}.fixed_case_matrix_not_used")
        if payload.get("semantic_owner") != "fixture_manager_structured_decision":
            blockers.append(f"{group_id}.semantic_owner_not_fixture_manager")
        count_keys = ("case_count", "evaluated_case_count")
    else:
        if payload.get("provider_call_ready") is not False:
            blockers.append(f"{group_id}.provider_call_ready")
        if payload.get("human_approval_required_before_live_provider") is not True:
            blockers.append(f"{group_id}.human_approval_before_live_missing")
        if payload.get("full_matrix_required") is not True:
            blockers.append(f"{group_id}.full_matrix_not_required")
        count_keys = ("case_count", "validated_response_count")
    for key in count_keys:
        if _int_value(summary.get(key)) != len(CONTEXT_LIVE_REQUIRED_CASE_IDS):
            blockers.append(f"{group_id}.{key}_mismatch")
    if group_id == "context_live_diagnostic_dry_run_evaluator":
        if _int_value(summary.get("blocked_case_count")) != 0:
            blockers.append(f"{group_id}.blocked_case_count_nonzero")
        if _int_value(summary.get("target_candidate_cases")) < 1:
            blockers.append(f"{group_id}.target_candidate_cases_missing")
        if _int_value(summary.get("ambiguity_cases")) < 1:
            blockers.append(f"{group_id}.ambiguity_cases_missing")
        if _int_value(summary.get("pending_pin_cases")) < 1:
            blockers.append(f"{group_id}.pending_pin_cases_missing")
    else:
        if _int_value(summary.get("blocked_response_count")) != 0:
            blockers.append(f"{group_id}.blocked_response_count_nonzero")
        if _int_value(summary.get("target_candidate_response_count")) < 1:
            blockers.append(f"{group_id}.target_candidate_response_missing")
        if _int_value(summary.get("ambiguity_preserved_response_count")) < 1:
            blockers.append(f"{group_id}.ambiguity_response_missing")
    return blockers


def context_holdout_plan_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _object_dict(payload.get("summary"))
    for flag in ("diagnostic_only", "fixture_only", "plan_only", "fixed_case_matrix_used"):
        if payload.get(flag) is not True:
            blockers.append(f"context_live_diagnostic_holdout_plan.{flag}_not_true")
    for flag in (
        "holdout_variants_withheld_from_default_live_prompt",
        "blocked_if_single_case_only",
        "human_review_required_before_promoting_failures",
    ):
        if payload.get(flag) is not True:
            blockers.append(f"context_live_diagnostic_holdout_plan.{flag}_not_true")
    for flag in ("ad_hoc_live_case_selection_allowed", "provider_optimized_case_selection_allowed"):
        if payload.get(flag) is not False:
            blockers.append(f"context_live_diagnostic_holdout_plan.{flag}_not_false")
    if payload.get("semantic_owner") != "future_live_manager_provider_when_human_approved":
        blockers.append("context_live_diagnostic_holdout_plan.semantic_owner_not_live_manager")
    if payload.get("deterministic_role") != "validate_case_selection_not_select_intent":
        blockers.append("context_live_diagnostic_holdout_plan.deterministic_role_wrong")
    if _int_value(summary.get("case_count")) != len(CONTEXT_LIVE_REQUIRED_CASE_IDS):
        blockers.append("context_live_diagnostic_holdout_plan.case_count_mismatch")
    if _int_value(summary.get("withheld_holdout_variant_count")) < len(CONTEXT_LIVE_REQUIRED_CASE_IDS) * 2:
        blockers.append("context_live_diagnostic_holdout_plan.withheld_holdout_count_too_low")
    if _int_value(summary.get("cases_with_holdouts")) != len(CONTEXT_LIVE_REQUIRED_CASE_IDS):
        blockers.append("context_live_diagnostic_holdout_plan.cases_with_holdouts_mismatch")
    for key in ("compound_cases", "ambiguity_cases", "pending_pin_cases", "target_candidate_cases"):
        if _int_value(summary.get(key)) < 1:
            blockers.append(f"context_live_diagnostic_holdout_plan.{key}_missing")
    return blockers
