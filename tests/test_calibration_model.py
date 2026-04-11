from __future__ import annotations

import pytest

from app.application.calibration_model import CalibrationModelInputs, build_calibration_model


def test_calibration_model_requires_the_v1_observation_window_and_count() -> None:
    result = build_calibration_model(
        CalibrationModelInputs(
            body_plan_estimated_tdee_kcal=2100,
            observation_window_days=13,
            body_observation_count=5,
            intake_coverage=0.95,
        )
    )

    assert result.calibration_posture == "insufficient_data"
    assert result.observation_quality_posture == "insufficient_data"
    assert result.proposal_eligibility is False
    assert result.operating_expenditure_estimate_kcal == 2100


def test_calibration_model_honors_the_80_percent_intake_coverage_boundary() -> None:
    result = build_calibration_model(
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

    assert result.calibration_posture == "logging_quality_first"
    assert result.logging_quality_posture == "logging_quality_first"
    assert result.intake_estimation_bias_posture == "likely_underestimate"
    assert result.operating_expenditure_estimate_kcal == 2100
    assert result.proposal_eligibility is False


def test_calibration_model_distinguishes_operating_expenditure_estimate_from_intake_bias_posture() -> None:
    result = build_calibration_model(
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

    assert result.calibration_posture == "calibration_candidate"
    assert result.operating_expenditure_estimate_kcal == 2190
    assert result.intake_estimation_bias_posture == "likely_underestimate"
    assert result.mismatch_attribution == "likely_intake_underestimate"
    assert result.proposal_eligibility is True


def test_calibration_model_promotes_strong_consistent_signal_to_high_confidence_mismatch() -> None:
    result = build_calibration_model(
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

    assert result.calibration_posture == "high_confidence_mismatch"
    assert result.calibration_confidence == "high"
    assert result.operating_expenditure_estimate_kcal == 2406
    assert result.mismatch_attribution == "likely_expenditure_shift"
    assert result.proposal_eligibility is True


def test_calibration_model_rejects_invalid_coverage() -> None:
    with pytest.raises(ValueError, match="intake_coverage"):
        build_calibration_model(
            CalibrationModelInputs(
                body_plan_estimated_tdee_kcal=2100,
                observation_window_days=14,
                body_observation_count=5,
                intake_coverage=1.2,
            )
        )
