from __future__ import annotations

from typing import Any

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import REQUIRED_CASE_IDS


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def holdout_plan_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _dict(payload.get("summary"))
    if payload.get("plan_only") is not True:
        blockers.append("context_live_diagnostic_holdout_plan.plan_only_not_true")
    if payload.get("fixture_only") is not True:
        blockers.append("context_live_diagnostic_holdout_plan.fixture_only_not_true")
    if payload.get("fixed_case_matrix_used") is not True:
        blockers.append("context_live_diagnostic_holdout_plan.fixed_case_matrix_not_used")
    if payload.get("holdout_variants_withheld_from_default_live_prompt") is not True:
        blockers.append("context_live_diagnostic_holdout_plan.holdouts_not_withheld")
    if payload.get("ad_hoc_live_case_selection_allowed") is not False:
        blockers.append("context_live_diagnostic_holdout_plan.ad_hoc_case_selection_allowed")
    if payload.get("provider_optimized_case_selection_allowed") is not False:
        blockers.append("context_live_diagnostic_holdout_plan.provider_optimized_case_selection_allowed")
    if payload.get("blocked_if_single_case_only") is not True:
        blockers.append("context_live_diagnostic_holdout_plan.single_case_blocker_missing")
    if _int(summary.get("case_count")) != len(REQUIRED_CASE_IDS):
        blockers.append("context_live_diagnostic_holdout_plan.case_count_mismatch")
    if _int(summary.get("withheld_holdout_variant_count")) < len(REQUIRED_CASE_IDS) * 2:
        blockers.append("context_live_diagnostic_holdout_plan.withheld_variant_count_too_low")
    if _int(summary.get("cases_with_holdouts")) != len(REQUIRED_CASE_IDS):
        blockers.append("context_live_diagnostic_holdout_plan.cases_with_holdouts_mismatch")
    if _int(summary.get("compound_cases")) < 1:
        blockers.append("context_live_diagnostic_holdout_plan.compound_case_missing")
    if _int(summary.get("ambiguity_cases")) < 1:
        blockers.append("context_live_diagnostic_holdout_plan.ambiguity_case_missing")
    return blockers


def holdout_plan_review_summary(payload: dict[str, Any]) -> dict[str, int]:
    summary = _dict(payload.get("summary"))
    return {
        "holdout_fixed_case_count": _int(summary.get("case_count")),
        "holdout_withheld_variant_count": _int(summary.get("withheld_holdout_variant_count")),
        "holdout_cases_with_holdouts": _int(summary.get("cases_with_holdouts")),
    }


__all__ = ["holdout_plan_blockers", "holdout_plan_review_summary"]
