from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.body.application.body_observation_service import (
    get_latest_weight_observation,
    load_body_observation_history,
)
from app.composition.body_budget_deficit_summary import build_body_budget_deficit_summary


def _date_window(*, local_date: str, window_days: int) -> list[str]:
    bounded_days = max(1, min(int(window_days), 31))
    end_date = datetime.fromisoformat(local_date).date()
    start_date = end_date - timedelta(days=bounded_days - 1)
    return [(start_date + timedelta(days=offset)).isoformat() for offset in range(bounded_days)]


def _day_payload(db: Session, *, user_id: int, local_date: str) -> dict[str, Any]:
    summary = build_body_budget_deficit_summary(db, user_id=user_id, local_date=local_date)
    latest_weight = get_latest_weight_observation(db, user_id=user_id, local_date=local_date)
    return {
        "local_date": local_date,
        "target_available": summary["target_available"],
        "target_source": summary["target_source"],
        "active_daily_target_kcal": summary["active_daily_target_kcal"],
        "recommended_target_kcal": summary["recommended_target_kcal"],
        "consumed_kcal": summary["consumed_kcal"],
        "adjustment_kcal": summary["adjustment_kcal"],
        "remaining_kcal": summary["remaining_kcal"],
        "estimated_daily_deficit_kcal": summary["estimated_daily_deficit_kcal"],
        "active_meal_count": summary["current_budget"]["active_meal_count"],
        "current_budget_ledger_present": summary["current_budget_ledger_present"],
        "latest_weight_kg": float(latest_weight.value) if latest_weight is not None else None,
        "latest_weight_observed_at": (
            latest_weight.observed_at.isoformat() if latest_weight is not None and latest_weight.observed_at else None
        ),
        "latest_weight_observation_id": latest_weight.observation_id if latest_weight is not None else None,
    }


def _window_weight_observations(
    db: Session,
    *,
    user_id: int,
    window_dates: list[str],
) -> list[Any]:
    if not window_dates:
        return []
    start_date = window_dates[0]
    end_date = window_dates[-1]
    return [
        observation
        for observation in load_body_observation_history(db, user_id=user_id, observation_type="weight")
        if start_date <= str(observation.local_date) <= end_date
    ]


def build_body_budget_weekly_progress(
    db: Session,
    *,
    user_id: int,
    local_date: str,
    window_days: int = 7,
) -> dict[str, Any]:
    window_dates = _date_window(local_date=local_date, window_days=window_days)
    days = [_day_payload(db, user_id=user_id, local_date=day) for day in window_dates]
    weights = _window_weight_observations(db, user_id=user_id, window_dates=window_dates)
    first_weight = weights[0] if weights else None
    latest_weight = weights[-1] if weights else None

    total_consumed = sum(int(day["consumed_kcal"] or 0) for day in days)
    total_remaining = sum(int(day["remaining_kcal"] or 0) for day in days if day["remaining_kcal"] is not None)
    estimated_weekly_deficit = sum(
        int(day["estimated_daily_deficit_kcal"] or 0)
        for day in days
        if day["estimated_daily_deficit_kcal"] is not None
    )

    return {
        "source_kind": "body_budget_weekly_progress",
        "read_only": True,
        "truth_owner": "composition_body_budget_weekly_read_model",
        "user_id": user_id,
        "window_start_date": window_dates[0],
        "window_end_date": window_dates[-1],
        "window_days": len(window_dates),
        "days": days,
        "logged_day_count": sum(1 for day in days if int(day["active_meal_count"] or 0) > 0),
        "target_available_day_count": sum(1 for day in days if day["target_available"] is True),
        "total_consumed_kcal": total_consumed,
        "total_remaining_kcal": total_remaining,
        "estimated_weekly_deficit_kcal": estimated_weekly_deficit,
        "weight_observation_count": len(weights),
        "first_weight_kg": float(first_weight.value) if first_weight is not None else None,
        "first_weight_observed_at": (
            first_weight.observed_at.isoformat() if first_weight is not None and first_weight.observed_at else None
        ),
        "first_weight_observation_id": first_weight.observation_id if first_weight is not None else None,
        "latest_weight_kg": float(latest_weight.value) if latest_weight is not None else None,
        "latest_weight_observed_at": (
            latest_weight.observed_at.isoformat() if latest_weight is not None and latest_weight.observed_at else None
        ),
        "latest_weight_observation_id": latest_weight.observation_id if latest_weight is not None else None,
        "weight_delta_kg": (
            round(float(latest_weight.value) - float(first_weight.value), 3)
            if latest_weight is not None and first_weight is not None
            else None
        ),
        "weight_delta_policy": "first_valid_then_last_valid_ordered_by_observed_at_then_id",
        "trend_interpretation_enabled": False,
        "automatic_calibration_enabled": False,
        "rescue_enabled": False,
        "recommendation_enabled": False,
        "proactive_enabled": False,
        "live_tool_calling": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
    }


__all__ = ["build_body_budget_weekly_progress"]
