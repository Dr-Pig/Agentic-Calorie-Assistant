from __future__ import annotations

from typing import Any

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)


def build_product_lab_calibration_fixture_inputs(
    *,
    insufficient_data: bool = False,
) -> dict[str, Any]:
    return {
        **build_product_lab_fixture_inputs(),
        "calibration_model_inputs": _calibration_model_inputs(
            insufficient_data=insufficient_data
        ),
        "calibration_current_budget_view": _calibration_current_budget_view(),
        "calibration_active_body_plan_view": _calibration_active_body_plan_view(),
        "calibration_current_budget_status": "on_track",
        "calibration_rescue_recovery_viability": "non_viable",
    }


def _calibration_model_inputs(*, insufficient_data: bool) -> dict[str, Any]:
    return {
        "body_plan_estimated_tdee_kcal": 2100,
        "observation_window_days": 7 if insufficient_data else 21,
        "body_observation_count": 3 if insufficient_data else 9,
        "intake_coverage": 0.93,
        "operating_expenditure_shift_kcal": -340,
        "trend_mismatch_consistency": 0.9,
        "trend_volatility": 0.1,
        "logging_gap_ratio": 0.05,
        "late_logged_meal_ratio": 0.05,
    }


def _calibration_current_budget_view() -> dict[str, Any]:
    return {
        "user_id": 1,
        "local_date": "2026-05-14",
        "budget_kcal": 1800,
        "consumed_kcal": 1450,
        "remaining_kcal": 350,
    }


def _calibration_active_body_plan_view() -> dict[str, Any]:
    return {
        "body_plan_id": 10,
        "user_id": 1,
        "plan_status": "active",
        "daily_budget_kcal": 1800,
        "recommended_target_kcal": 1800,
        "safety_floor_kcal": 1200,
        "estimated_tdee": 2100,
        "target_pace_kg_per_week": 0.5,
        "profile_status": "ready",
        "plan_source": "product_lab_fixture",
    }


__all__ = ["build_product_lab_calibration_fixture_inputs"]
