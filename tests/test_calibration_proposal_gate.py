from __future__ import annotations

from app.body.application.calibration_model import CalibrationModelInputs, build_calibration_model
from app.body.application.calibration_proposal_gate import (
    ALL_OPTION_FAMILIES,
    CalibrationProposalGateInputs,
    build_calibration_proposal_gate,
)


def _build_candidate_model():
    return build_calibration_model(
        CalibrationModelInputs(
            body_plan_estimated_tdee_kcal=2100,
            observation_window_days=14,
            body_observation_count=6,
            intake_coverage=0.80,
            operating_expenditure_shift_kcal=240,
            trend_mismatch_consistency=0.75,
            trend_volatility=0.2,
            logging_gap_ratio=0.18,
            late_logged_meal_ratio=0.22,
        )
    )


def _build_high_confidence_model():
    return build_calibration_model(
        CalibrationModelInputs(
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
    )


def test_calibration_proposal_gate_blocks_logging_quality_first_and_monitor_only_cases() -> None:
    logging_quality_first_model = build_calibration_model(
        CalibrationModelInputs(
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
    )
    monitor_only_model = build_calibration_model(
        CalibrationModelInputs(
            body_plan_estimated_tdee_kcal=2100,
            observation_window_days=14,
            body_observation_count=6,
            intake_coverage=0.95,
            operating_expenditure_shift_kcal=80,
            trend_mismatch_consistency=0.5,
            trend_volatility=0.2,
        )
    )

    logging_quality_first_gate = build_calibration_proposal_gate(
        CalibrationProposalGateInputs(
            calibration_result=logging_quality_first_model,
            current_budget_status="on_track",
            active_body_plan_status="active",
        )
    )
    monitor_only_gate = build_calibration_proposal_gate(
        CalibrationProposalGateInputs(
            calibration_result=monitor_only_model,
            current_budget_status="on_track",
            active_body_plan_status="active",
        )
    )

    assert logging_quality_first_gate.proposal_eligibility is False
    assert logging_quality_first_gate.allowed_option_families == ()
    assert logging_quality_first_gate.blocked_option_families == ALL_OPTION_FAMILIES
    assert any("logging_quality_first" in reason for reason in logging_quality_first_gate.gate_rationale)

    assert monitor_only_gate.proposal_eligibility is False
    assert monitor_only_gate.allowed_option_families == ()
    assert monitor_only_gate.blocked_option_families == ALL_OPTION_FAMILIES
    assert any("monitor_only" in reason for reason in monitor_only_gate.gate_rationale)


def test_calibration_proposal_gate_allows_only_budget_adjustment_for_medium_confidence_candidate() -> None:
    candidate_model = _build_candidate_model()

    gate = build_calibration_proposal_gate(
        CalibrationProposalGateInputs(
            calibration_result=candidate_model,
            current_budget_status="tight",
            active_body_plan_status="active",
        )
    )

    assert gate.proposal_eligibility is True
    assert gate.primary_policy_posture == "calibration_candidate"
    assert gate.allowed_option_families == ("budget_adjustment",)
    assert gate.blocked_option_families == (
        "monitor_only",
        "logging_quality_first",
        "pace_adjustment",
        "plan_reset",
    )
    assert "budget_adjustment" in gate.gate_rationale[-1]


def test_calibration_proposal_gate_blocks_flow_when_a_recent_similar_proposal_is_open() -> None:
    candidate_model = _build_candidate_model()

    gate = build_calibration_proposal_gate(
        CalibrationProposalGateInputs(
            calibration_result=candidate_model,
            current_budget_status="tight",
            active_body_plan_status="active",
            recent_similar_proposal_open=True,
        )
    )

    assert gate.proposal_eligibility is False
    assert gate.allowed_option_families == ()
    assert gate.blocked_option_families == ALL_OPTION_FAMILIES
    assert any("open" in reason for reason in gate.gate_rationale)


def test_calibration_proposal_gate_allows_plan_reset_only_when_rescue_is_non_viable() -> None:
    high_confidence_model = _build_high_confidence_model()

    gate = build_calibration_proposal_gate(
        CalibrationProposalGateInputs(
            calibration_result=high_confidence_model,
            current_budget_status="over_budget",
            active_body_plan_status="active",
            rescue_recovery_viability="non_viable",
        )
    )

    assert gate.proposal_eligibility is True
    assert gate.primary_policy_posture == "high_confidence_mismatch"
    assert gate.allowed_option_families == ("budget_adjustment", "pace_adjustment", "plan_reset")
    assert gate.blocked_option_families == ("monitor_only", "logging_quality_first")
