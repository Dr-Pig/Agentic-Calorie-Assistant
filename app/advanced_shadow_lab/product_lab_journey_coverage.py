from __future__ import annotations

from typing import Any, Mapping


IN_SCOPE_JOURNEY_IDS = [
    "A", "B", "C", "D", "E", "F", "F2", "G", "H", "I",
    "J", "K", "L", "M", "N", "Q", "S", "T", "U", "V",
]
EXCLUDED_JOURNEY_IDS = ["O", "P", "R"]
COVERED = "covered_by_existing_executable_evidence"
MISSING_SCENARIO = "implemented_but_missing_executable_scenario"
CAPABILITY_GAP = "product_capability_gap"
NEXT_SLICE_BY_ID = {
    "Q": "pre_meal_planning_recommendation_lab",
    "S": "swap_suggestion_memory_lab",
    "T": "planned_event_all_day_allocation_e2e_lab",
    "U": "exercise_bonus_budget_lab",
    "V": "weekly_insight_proactive_lab",
}


def build_product_lab_journey_coverage_summary(
    _: Mapping[str, Any],
) -> dict[str, Any]:
    rows = [_row(journey_id) for journey_id in IN_SCOPE_JOURNEY_IDS]
    covered = _ids_with(rows, COVERED)
    missing_scenarios = _ids_with(rows, MISSING_SCENARIO)
    capability_gaps = _ids_with(rows, CAPABILITY_GAP)
    return {
        "journey_coverage_owner": "app/advanced_shadow_lab/product_lab_journey_coverage.py",
        "journey_coverage_consumer": "advanced_product_lab_closure_summary",
        "journey_coverage_retirement_trigger": "approved_full_product_runtime_activation",
        "in_scope_journey_ids": list(IN_SCOPE_JOURNEY_IDS),
        "excluded_journey_ids": list(EXCLUDED_JOURNEY_IDS),
        "excluded_journey_reason": "photo_menu_scan_and_voice_input_deferred_by_product_decision",
        "journey_coverage_rows": rows,
        "covered_by_existing_executable_evidence_journey_ids": covered,
        "implemented_but_missing_executable_scenario_journey_ids": missing_scenarios,
        "product_capability_gap_journey_ids": capability_gaps,
        "advanced_product_lab_journey_coverage_closed": not (
            missing_scenarios or capability_gaps
        ),
        "next_product_capability_slice": _next_slice(missing_scenarios, capability_gaps),
        "new_report_family_created": False,
    }


def _row(journey_id: str) -> dict[str, Any]:
    status = _status(journey_id)
    return {
        "journey_id": journey_id,
        "coverage_status": status,
        "truth_owner": _truth_owner(journey_id),
        "executable_evidence_refs": _evidence_refs(journey_id, status),
        "next_build_slice": NEXT_SLICE_BY_ID.get(journey_id, ""),
        "claim_boundary": "coverage_index_not_readiness_claim",
        "mainline_activation_allowed": False,
        "semantic_decision_inferred_by_runner": False,
        "do_not_cross": _do_not_cross(journey_id),
    }


def _status(journey_id: str) -> str:
    if journey_id in {"S", "U", "V"}:
        return CAPABILITY_GAP
    if journey_id == "T":
        return MISSING_SCENARIO
    return COVERED


def _truth_owner(journey_id: str) -> str:
    return {
        "Q": "recommendation_pre_meal_planning_product_spec",
        "S": "swap_suggestion_and_memory_product_spec",
        "T": "planned_event_budget_allocation_product_spec",
        "U": "exercise_event_and_budget_ledger_product_spec",
        "V": "proactive_weekly_insight_product_spec",
    }.get(journey_id, "existing_product_runtime_and_lab_contracts")


def _evidence_refs(journey_id: str, status: str) -> list[str]:
    if status != COVERED:
        return []
    refs = {
        "A": ["tests/test_onboarding.py"],
        "B": ["tests/test_product_loop_mvp_read_model.py"],
        "C": ["tests/test_accurate_intake_basket_holdout_regression.py"],
        "D": ["tests/test_accurate_intake_basket_holdout_regression.py"],
        "E": ["tests/test_product_loop_mvp_read_model.py"],
        "F": ["tests/test_advanced_product_lab_rescue_runtime.py"],
        "F2": ["tests/test_advanced_product_lab_planned_event_rescue.py"],
        "G": ["tests/test_weight_route_body_plan_boundary.py"],
        "H": ["tests/test_accurate_intake_body_observation_same_truth_gate.py"],
        "I": ["tests/test_advanced_product_lab_calibration_ux.py"],
        "J": ["tests/test_advanced_product_lab_no_plan_degraded.py"],
        "K": ["tests/test_product_loop_mvp_read_model.py"],
        "L": ["tests/test_advanced_product_lab_recommendation_runtime.py"],
        "M": ["tests/test_advanced_product_lab_memory_vertical.py"],
        "N": ["tests/test_advanced_product_lab_proactive_runtime.py"],
        "Q": ["tests/test_advanced_product_lab_premeal_planning.py"],
    }
    return list(refs[journey_id])


def _do_not_cross(journey_id: str) -> list[str]:
    if journey_id == "U":
        return [
            "no_body_plan_tdee_rewrite",
            "no_production_ledger_write",
            "no_scheduler_or_notification",
        ]
    return ["no_mainline_activation", "no_product_semantics_from_fixture_labels"]


def _ids_with(rows: list[Mapping[str, Any]], status: str) -> list[str]:
    return [str(row["journey_id"]) for row in rows if row["coverage_status"] == status]


def _next_slice(missing_scenarios: list[str], capability_gaps: list[str]) -> str:
    ids = [*capability_gaps, *missing_scenarios]
    return NEXT_SLICE_BY_ID[ids[0]] if ids else ""


__all__ = ["IN_SCOPE_JOURNEY_IDS", "build_product_lab_journey_coverage_summary"]
