from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.shared.domain import ActiveBodyPlanView, CurrentBudgetView

from .body_calibration_service import BodyCalibrationDiagnosticRequest, build_body_calibration_diagnostic
from .calibration_model import CalibrationModelInputs


_REQUIRED_CASE_IDS = (
    "logging_quality_first_preview_no_plan_change",
    "budget_adjustment_preview_requires_stored_accept",
    "plan_reset_hidden_until_rescue_non_viable",
    "recent_open_proposal_blocks_new_proposal",
)
_FALSE_FIELDS = (
    "runtime_connected",
    "runtime_truth_changed",
    "mutation_changed",
    "action_route_mounted",
    "proposal_container_created",
    "stored_action_applied",
    "body_plan_mutated",
    "ledger_entry_created",
    "current_budget_view_refreshed",
)


def _current_budget_view(*, remaining_kcal: int = -200) -> CurrentBudgetView:
    return CurrentBudgetView(user_id=1, local_date="2026-05-14", budget_kcal=1800, remaining_kcal=remaining_kcal)


def _active_body_plan_view() -> ActiveBodyPlanView:
    return ActiveBodyPlanView(
        body_plan_id=10,
        user_id=1,
        plan_status="active",
        daily_budget_kcal=1800,
        recommended_target_kcal=1800,
        safety_floor_kcal=1200,
        estimated_tdee=2100,
        target_pace_kg_per_week=0.5,
        profile_status="ready",
    )


def _logging_quality_inputs() -> CalibrationModelInputs:
    return CalibrationModelInputs(
        body_plan_estimated_tdee_kcal=2100,
        observation_window_days=14,
        body_observation_count=5,
        intake_coverage=0.79,
        operating_expenditure_shift_kcal=260,
        trend_mismatch_consistency=0.8,
        trend_volatility=0.2,
        logging_gap_ratio=0.2,
        late_logged_meal_ratio=0.3,
    )


def _high_confidence_inputs() -> CalibrationModelInputs:
    return CalibrationModelInputs(
        body_plan_estimated_tdee_kcal=2100,
        observation_window_days=21,
        body_observation_count=9,
        intake_coverage=0.93,
        operating_expenditure_shift_kcal=340,
        trend_mismatch_consistency=0.9,
        trend_volatility=0.1,
        logging_gap_ratio=0.05,
        late_logged_meal_ratio=0.05,
    )


def _diagnostic(
    *,
    model_inputs: CalibrationModelInputs,
    current_budget_status: str = "over_budget",
    rescue_recovery_viability: str = "viable",
    recent_similar_proposal_open: bool = False,
):
    return build_body_calibration_diagnostic(
        BodyCalibrationDiagnosticRequest(
            model_inputs=model_inputs,
            current_budget_status=current_budget_status,  # type: ignore[arg-type]
            rescue_recovery_viability=rescue_recovery_viability,  # type: ignore[arg-type]
            recent_similar_proposal_open=recent_similar_proposal_open,
            current_budget_view=_current_budget_view(),
            active_body_plan_view=_active_body_plan_view(),
        )
    )


def _base_case(case_id: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "claim_scope": "calibration_proposal_no_runtime_boundary",
        "semantic_owner": "calibration_model_and_proposal_policy",
        "deterministic_role": "gate_policy_and_mutation_boundary_validation",
        **dict.fromkeys(_FALSE_FIELDS, False),
    }


def _policy_case(case_id: str, result: Any) -> dict[str, Any]:
    policy = result.proposal_policy_packet
    actions = {action["action"]: action for action in result.response.quick_actions}
    accept = actions.get("accept_calibration_proposal", {})
    return _base_case(case_id) | {
        "proposal_eligibility": result.gate_result.proposal_eligibility,
        "proposal_family": policy["proposal_family"],
        "top_option_family": policy["top_option_family"],
        "allowed_option_families": policy["allowed_option_families"],
        "plan_change_required": policy["plan_change_required"],
        "requires_accept_before_plan_mutation": policy["requires_accept_before_plan_mutation"],
        "plan_mutation_authorized": policy["plan_mutation_authorized"],
        "ledger_mutation_authorized": policy["ledger_mutation_authorized"],
        "accept_action_requires_proposal_container_id": bool(accept.get("requires_proposal_container_id")),
        "accept_action_raw_text_authorized_mutation": bool(accept.get("raw_text_authorized_mutation")),
    }


def _cases() -> list[dict[str, Any]]:
    logging = _diagnostic(
        model_inputs=_logging_quality_inputs(),
        current_budget_status="on_track",
    )
    budget = _diagnostic(model_inputs=_high_confidence_inputs())
    reset = _diagnostic(
        model_inputs=_high_confidence_inputs(),
        rescue_recovery_viability="non_viable",
    )
    blocked = _diagnostic(
        model_inputs=_high_confidence_inputs(),
        recent_similar_proposal_open=True,
    )
    reset_cards = {card["option_type"]: card for card in reset.response.proposal_cards}
    return [
        _policy_case("logging_quality_first_preview_no_plan_change", logging),
        _policy_case("budget_adjustment_preview_requires_stored_accept", budget),
        _policy_case("plan_reset_hidden_until_rescue_non_viable", reset)
        | {
            "rescue_recovery_viability": "non_viable",
            "primary_option_family": reset.response.proposal_cards[0]["option_type"],
            "plan_reset_default_visibility": reset_cards["plan_reset"]["default_visibility"],
        },
        _base_case("recent_open_proposal_blocks_new_proposal")
        | {
            "proposal_eligibility": blocked.gate_result.proposal_eligibility,
            "allowed_option_families": list(blocked.gate_result.allowed_option_families),
            "blocked_reason_contains_open_proposal": any(
                "open" in reason for reason in blocked.gate_result.gate_rationale
            ),
        },
    ]


def _validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if [str(case.get("case_id") or "") for case in cases] != list(_REQUIRED_CASE_IDS):
        blockers.append("required_case_order_mismatch")
    for case in cases:
        case_id = str(case.get("case_id") or "unknown")
        for field in _FALSE_FIELDS:
            if case.get(field) is not False:
                blockers.append(f"{case_id}.{field}")
    return blockers


def build_calibration_proposal_boundary_contract_artifact() -> dict[str, Any]:
    cases = _cases()
    blockers = _validate_cases(cases)
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_calibration_proposal_boundary_contract",
        "status": "pass" if not blockers else "fail",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "owner": "app/body",
        "consumer": "future calibration runtime activation slices",
        "retirement_trigger": "approved calibration_action_runtime_activation_plan",
        "local_only": True,
        "diagnostic_only": True,
        "fixture_only": True,
        **dict.fromkeys(_FALSE_FIELDS, False),
        "best_practice_evidence": {
            "required": False,
            "rationale": "fixture-only boundary artifact over existing calibration diagnostic service",
        },
        "blockers": blockers,
        "cases": cases,
    }


__all__ = ["build_calibration_proposal_boundary_contract_artifact"]
