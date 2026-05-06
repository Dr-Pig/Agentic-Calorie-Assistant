from __future__ import annotations

from typing import Any

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS as CONTEXT_LIVE_REQUIRED_CASE_IDS,
)


OPTIONAL_LIVE_EVIDENCE_ALLOWED_FLAGS = {
    "context_live_diagnostic_review_pack": {
        "live_llm_invoked",
        "live_provider_invoked",
    },
    "context_live_diagnostic_gate": {
        "live_llm_invoked",
        "live_provider_invoked",
    },
}

CONTEXT_LIVE_GATE_REQUIRED_ARTIFACT_PATHS = (
    "context_live_diagnostic_case_matrix",
    "context_live_diagnostic_anti_overfit_guard",
    "context_live_diagnostic_holdout_plan",
    "context_live_provider_input_preflight",
    "context_live_response_contract_dry_run",
    "context_live_diagnostic_canary",
    "context_live_diagnostic_review_pack",
)


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _context_live_review_pack_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _object_dict(payload.get("summary"))
    status = _status(payload)
    if payload.get("diagnostic_only") is not True:
        blockers.append("context_live_diagnostic_review_pack.diagnostic_only_not_true")
    if payload.get("aggregate_only") is not True:
        blockers.append("context_live_diagnostic_review_pack.aggregate_only_not_true")
    if payload.get("human_review_required") is not True:
        blockers.append("context_live_diagnostic_review_pack.human_review_required_missing")
    if payload.get("fixed_case_matrix_used") is not True:
        blockers.append("context_live_diagnostic_review_pack.fixed_case_matrix_not_used")
    if _int_value(summary.get("fixed_case_count")) != len(CONTEXT_LIVE_REQUIRED_CASE_IDS):
        blockers.append("context_live_diagnostic_review_pack.fixed_case_count_mismatch")
    if _int_value(summary.get("dry_run_validated_response_count")) != len(
        CONTEXT_LIVE_REQUIRED_CASE_IDS
    ):
        blockers.append(
            "context_live_diagnostic_review_pack.dry_run_validated_response_count_mismatch"
        )
    if _int_value(summary.get("dry_run_blocked_response_count")) != 0:
        blockers.append("context_live_diagnostic_review_pack.dry_run_blocked_response_count_nonzero")
    if status == "context_live_diagnostic_review_ready_with_live_canary":
        if payload.get("live_llm_invoked") is not True:
            blockers.append("context_live_diagnostic_review_pack.live_llm_invoked_not_true")
        if payload.get("live_provider_invoked") is not True:
            blockers.append("context_live_diagnostic_review_pack.live_provider_invoked_not_true")
        if payload.get("live_canary_status") != "live_diagnostic_pass":
            blockers.append("context_live_diagnostic_review_pack.live_canary_status_not_pass")
        if _int_value(summary.get("live_provider_output_count")) != len(
            CONTEXT_LIVE_REQUIRED_CASE_IDS
        ):
            blockers.append("context_live_diagnostic_review_pack.live_provider_output_count_mismatch")
        if _int_value(summary.get("live_blocked_response_count")) != 0:
            blockers.append("context_live_diagnostic_review_pack.live_blocked_response_count_nonzero")
        if _int_value(summary.get("live_target_candidate_response_count")) < 1:
            blockers.append("context_live_diagnostic_review_pack.live_target_candidate_response_missing")
        if _int_value(summary.get("live_ambiguity_preserved_response_count")) < 1:
            blockers.append("context_live_diagnostic_review_pack.live_ambiguity_response_missing")
    else:
        if payload.get("live_llm_invoked") is not False:
            blockers.append("context_live_diagnostic_review_pack.unexpected_live_llm_invoked")
        if payload.get("live_provider_invoked") is not False:
            blockers.append("context_live_diagnostic_review_pack.unexpected_live_provider_invoked")
    return blockers


def _context_live_gate_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _object_dict(payload.get("summary"))
    artifact_paths = _object_dict(payload.get("artifact_paths"))
    status = _status(payload)
    if payload.get("diagnostic_only") is not True:
        blockers.append("context_live_diagnostic_gate.diagnostic_only_not_true")
    if payload.get("local_only") is not True:
        blockers.append("context_live_diagnostic_gate.local_only_not_true")
    if payload.get("fixed_case_matrix_used") is not True:
        blockers.append("context_live_diagnostic_gate.fixed_case_matrix_not_used")
    if payload.get("full_matrix_live_probe_required") is not True:
        blockers.append("context_live_diagnostic_gate.full_matrix_live_probe_not_required")
    if payload.get("ad_hoc_live_case_selection_allowed") is not False:
        blockers.append("context_live_diagnostic_gate.ad_hoc_live_case_selection_allowed")
    if payload.get("anti_overfit_guard_required") is not True:
        blockers.append("context_live_diagnostic_gate.anti_overfit_guard_not_required")
    if payload.get("holdout_plan_required") is not True:
        blockers.append("context_live_diagnostic_gate.holdout_plan_not_required")
    if payload.get("response_contract_dry_run_required") is not True:
        blockers.append("context_live_diagnostic_gate.response_contract_dry_run_not_required")
    for path_id in CONTEXT_LIVE_GATE_REQUIRED_ARTIFACT_PATHS:
        if not artifact_paths.get(path_id):
            blockers.append(f"context_live_diagnostic_gate.artifact_paths.{path_id}_missing")
    if _int_value(summary.get("fixed_case_count")) != len(CONTEXT_LIVE_REQUIRED_CASE_IDS):
        blockers.append("context_live_diagnostic_gate.fixed_case_count_mismatch")
    if _int_value(summary.get("dry_run_validated_response_count")) != len(
        CONTEXT_LIVE_REQUIRED_CASE_IDS
    ):
        blockers.append("context_live_diagnostic_gate.dry_run_validated_response_count_mismatch")
    if status == "context_live_diagnostic_gate_ready_with_live_canary":
        if payload.get("review_pack_status") != "context_live_diagnostic_review_ready_with_live_canary":
            blockers.append("context_live_diagnostic_gate.review_pack_status_not_live_ready")
        if payload.get("canary_status") != "live_diagnostic_pass":
            blockers.append("context_live_diagnostic_gate.canary_status_not_pass")
        if payload.get("live_llm_invoked") is not True:
            blockers.append("context_live_diagnostic_gate.live_llm_invoked_not_true")
        if payload.get("live_provider_invoked") is not True:
            blockers.append("context_live_diagnostic_gate.live_provider_invoked_not_true")
        if _int_value(summary.get("live_provider_output_count")) != len(
            CONTEXT_LIVE_REQUIRED_CASE_IDS
        ):
            blockers.append("context_live_diagnostic_gate.live_provider_output_count_mismatch")
        if _int_value(summary.get("live_blocked_response_count")) != 0:
            blockers.append("context_live_diagnostic_gate.live_blocked_response_count_nonzero")
    else:
        if payload.get("review_pack_status") != "context_live_diagnostic_review_ready_without_live_canary":
            blockers.append("context_live_diagnostic_gate.review_pack_status_not_non_live_ready")
        if payload.get("live_llm_invoked") is not False:
            blockers.append("context_live_diagnostic_gate.unexpected_live_llm_invoked")
        if payload.get("live_provider_invoked") is not False:
            blockers.append("context_live_diagnostic_gate.unexpected_live_provider_invoked")
    return blockers


def context_live_optional_group_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    if group_id == "context_live_diagnostic_review_pack":
        return _context_live_review_pack_blockers(payload)
    if group_id == "context_live_diagnostic_gate":
        return _context_live_gate_blockers(payload)
    return []


def context_live_review_state(payload: dict[str, Any]) -> tuple[str, str, bool]:
    status = _status(payload)
    if status == "context_live_diagnostic_review_ready_with_live_canary":
        return "live_canary_passed", "context_only_live_diagnostic_passed_not_full_e2e", True
    if status == "context_live_diagnostic_review_ready_without_live_canary":
        return "ready_without_live_canary", "context_live_review_ready_without_live_canary", False
    return "not_provided", "not_provided", False


def context_live_gate_state(payload: dict[str, Any]) -> tuple[str, str, bool]:
    status = _status(payload)
    if status == "context_live_diagnostic_gate_ready_with_live_canary":
        return (
            "gate_live_canary_passed",
            "context_only_live_diagnostic_gate_passed_not_full_e2e",
            True,
        )
    if status == "context_live_diagnostic_gate_ready_without_live_canary":
        return "gate_ready_without_live_canary", "context_live_gate_ready_without_live_canary", False
    return "not_provided", "not_provided", False
