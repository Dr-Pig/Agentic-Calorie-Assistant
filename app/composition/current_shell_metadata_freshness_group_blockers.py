from __future__ import annotations

from typing import Any

from app.composition.current_shell_metadata_freshness_constants import MIN_CONTEXT_SUMMARY_COUNTS


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _current_gap_count(payload: dict[str, Any]) -> int:
    summary = _object_dict(payload.get("summary"))
    if "short_term_context_current_gap_scenarios" in payload:
        return _int_value(payload.get("short_term_context_current_gap_scenarios"))
    if "short_term_context_current_gap_scenarios" in summary:
        return _int_value(summary.get("short_term_context_current_gap_scenarios"))
    return _int_value(summary.get("short_term_runtime_replay_current_gap_scenarios"))


def _context_quality_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("runtime_trace_input_used") is not True:
        blockers.append("context_quality_pack.runtime_trace_input_missing")
    if payload.get("short_term_context_runtime_replay_checked") is not True:
        blockers.append("context_quality_pack.short_term_runtime_replay_missing")
    summary = _object_dict(payload.get("summary"))
    for key, minimum in MIN_CONTEXT_SUMMARY_COUNTS.items():
        if _int_value(summary.get(key)) < minimum:
            suffix = "missing" if minimum == 1 else "too_low"
            blockers.append(f"context_quality_pack.{key}_{suffix}")
    if _current_gap_count(payload) != 0:
        blockers.append("context_quality_pack.short_term_context_current_gap_scenarios_present")
    return blockers


def _product_pages_visual_qa_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for key in (
        "browser_executed",
        "three_distinct_pages_verified",
        "chat_surface_verified",
        "today_surface_verified",
        "body_surface_verified",
        "visible_trace_debug_terms_absent",
    ):
        if payload.get(key) is not True:
            blockers.append(f"product_pages_visual_qa.{key}_not_true")
    return blockers


def _decision_pack_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("ready_for_live_diagnostic_decision") is not False:
        blockers.append("pl_ce_local_review_decision_pack.ready_for_live_diagnostic_decision_not_false")
    if payload.get("ready_for_fdb_integration") is not False:
        blockers.append("pl_ce_local_review_decision_pack.ready_for_fdb_integration_not_false")
    return blockers


def _local_mvp_candidate_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("activation_gate_status") != "blocked_pending_human_and_browser_activation":
        blockers.append("pl_ce_local_mvp_candidate_bundle.activation_gate_status_missing")
    fooddb_dependency = _object_dict(payload.get("fooddb_dependency"))
    if fooddb_dependency.get("fooddb_artifact_status") != "blocked_waiting_for_fdb_artifact":
        blockers.append("pl_ce_local_mvp_candidate_bundle.fooddb_stop_gate_missing")
    if fooddb_dependency.get("ready_for_fdb_integration") is not False:
        blockers.append("pl_ce_local_mvp_candidate_bundle.fooddb_integration_not_blocked")
    return blockers


def _activation_manifest_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("human_review_required") is not True:
        blockers.append("pl_ce_activation_review_manifest.human_review_required_not_true")
    if payload.get("live_diagnostic_human_approval_required") is not True:
        blockers.append("pl_ce_activation_review_manifest.live_human_approval_not_required")
    stop_gates = _object_dict(payload.get("remaining_stop_gates"))
    if stop_gates.get("fooddb_artifact_status") != "blocked_waiting_for_fdb_artifact":
        blockers.append("pl_ce_activation_review_manifest.fooddb_stop_gate_missing")
    if stop_gates.get("live_provider_status") != "blocked_pending_human_approval":
        blockers.append("pl_ce_activation_review_manifest.live_provider_stop_gate_missing")
    return blockers


def _ui_same_truth_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("frontend_semantic_owner") is not False:
        blockers.append("ui_same_truth_render_contract.frontend_semantic_owner_not_false")
    if payload.get("runtime_truth_changed") is not False:
        blockers.append("ui_same_truth_render_contract.runtime_truth_changed_not_false")
    if payload.get("mutation_changed") is not False:
        blockers.append("ui_same_truth_render_contract.mutation_changed_not_false")
    return blockers


def _group_specific_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    if group_id == "context_quality_pack":
        return _context_quality_blockers(payload)
    if group_id == "product_pages_visual_qa":
        return _product_pages_visual_qa_blockers(payload)
    if group_id == "pl_ce_local_review_decision_pack":
        return _decision_pack_blockers(payload)
    if group_id == "pl_ce_local_mvp_candidate_bundle":
        return _local_mvp_candidate_blockers(payload)
    if group_id == "pl_ce_activation_review_manifest":
        return _activation_manifest_blockers(payload)
    if group_id == "ui_same_truth_render_contract":
        return _ui_same_truth_blockers(payload)
    return []
