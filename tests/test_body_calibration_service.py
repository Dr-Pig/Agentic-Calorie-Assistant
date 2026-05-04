from __future__ import annotations

from app.body.application.body_calibration_service import (
    BodyCalibrationDiagnosticRequest,
    build_body_calibration_diagnostic,
)
from app.body.application.calibration_model import CalibrationModelInputs
from app.shared.domain import ActiveBodyPlanView, CurrentBudgetView


def _current_budget_view() -> CurrentBudgetView:
    return CurrentBudgetView(
        user_id=1,
        local_date="2026-05-04",
        budget_kcal=1800,
        remaining_kcal=900,
    )


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


def test_logging_quality_first_diagnostic_surfaces_non_mutating_candidate_and_no_runtime_claims() -> None:
    result = build_body_calibration_diagnostic(
        BodyCalibrationDiagnosticRequest(
            model_inputs=CalibrationModelInputs(
                body_plan_estimated_tdee_kcal=2100,
                observation_window_days=14,
                body_observation_count=5,
                intake_coverage=0.79,
                operating_expenditure_shift_kcal=260,
                trend_mismatch_consistency=0.8,
                trend_volatility=0.2,
                logging_gap_ratio=0.2,
                late_logged_meal_ratio=0.3,
            ),
            current_budget_status="on_track",
            current_budget_view=_current_budget_view(),
            active_body_plan_view=_active_body_plan_view(),
        )
    )

    assert result.calibration_result.calibration_posture == "logging_quality_first"
    assert result.response.proposal_family == "logging_quality_first"
    assert result.response.top_option is not None
    assert result.response.top_option.option_type == "logging_quality_first"
    assert result.proposal_policy_packet["top_option_family"] == "logging_quality_first"
    assert result.proposal_policy_packet["proposal_family"] == "logging_quality_first"
    assert result.proposal_policy_packet["plan_change_required"] is False
    assert result.proposal_policy_packet["requires_accept_before_plan_mutation"] is False
    assert result.proposal_policy_packet["plan_mutation_authorized"] is False
    assert result.proposal_policy_packet["ledger_mutation_authorized"] is False
    assert result.proposal_policy_packet["active_plan_mutation_allowed_now"] is False
    assert result.proposal_policy_packet["llm_role"] == "explain_only"
    assert result.trace_envelope["live_tool_calling"] is False
    assert result.trace_envelope["automatic_calibration_enabled"] is False
    assert result.trace_envelope["rescue_enabled"] is False
    assert result.trace_envelope["recommendation_enabled"] is False
    assert result.trace_envelope["proactive_enabled"] is False


def test_high_confidence_mismatch_diagnostic_surfaces_budget_candidate_without_preview_mutation_authority() -> None:
    result = build_body_calibration_diagnostic(
        BodyCalibrationDiagnosticRequest(
            model_inputs=CalibrationModelInputs(
                body_plan_estimated_tdee_kcal=2100,
                observation_window_days=21,
                body_observation_count=9,
                intake_coverage=0.93,
                operating_expenditure_shift_kcal=340,
                trend_mismatch_consistency=0.9,
                trend_volatility=0.1,
                logging_gap_ratio=0.05,
                late_logged_meal_ratio=0.05,
            ),
            current_budget_status="over_budget",
            rescue_recovery_viability="non_viable",
            current_budget_view=_current_budget_view(),
            active_body_plan_view=_active_body_plan_view(),
        )
    )

    assert result.calibration_result.calibration_posture == "high_confidence_mismatch"
    assert result.gate_result.allowed_option_families == (
        "budget_adjustment",
        "pace_adjustment",
        "plan_reset",
    )
    assert result.response.proposal_family == "budget_adjustment"
    assert result.response.top_option is not None
    assert result.response.top_option.option_type == "budget_adjustment"
    assert result.proposal_policy_packet["top_option_family"] == "budget_adjustment"
    assert result.proposal_policy_packet["proposal_family"] == "budget_adjustment"
    assert result.proposal_policy_packet["allowed_option_families"] == [
        "budget_adjustment",
        "pace_adjustment",
        "plan_reset",
    ]
    assert result.proposal_policy_packet["plan_change_required"] is True
    assert result.proposal_policy_packet["requires_accept_before_plan_mutation"] is True
    assert result.proposal_policy_packet["plan_mutation_authorized"] is False
    assert result.proposal_policy_packet["ledger_mutation_authorized"] is False
    assert result.proposal_policy_packet["active_plan_mutation_allowed_now"] is False
    assert result.proposal_policy_packet["llm_role"] == "explain_only"
