from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def read_body_plan_tool(db: Session, *, user_id: int) -> Any:
    from ...body.application import build_active_body_plan_view

    return build_active_body_plan_view(db, user_id=user_id)


def read_day_budget_tool(db: Session, *, user_id: int, local_date: str) -> Any:
    from ...budget.application import build_current_budget_view

    return build_current_budget_view(db, user_id=user_id, local_date=local_date)


def read_active_meal_tool(db: Session, *, user_id: int, local_date: str) -> dict[str, Any] | None:
    budget = read_day_budget_tool(db, user_id=user_id, local_date=local_date)
    if not budget.meals:
        return None
    latest_meal = max(
        budget.meals,
        key=lambda meal: meal.occurred_at.isoformat() if meal.occurred_at is not None else "",
    )
    return {
        "meal_thread_id": latest_meal.meal_thread_id,
        "meal_version_id": latest_meal.meal_version_id,
        "meal_title": latest_meal.meal_title,
        "total_kcal": latest_meal.total_kcal,
    }


def compare_against_budget_tool(
    *,
    current_budget_view: Any,
    estimated_kcal: int,
    replaced_kcal: int = 0,
) -> dict[str, Any]:
    consumed_before = int(current_budget_view.consumed_kcal or 0)
    budget_kcal = int(current_budget_view.budget_kcal or 0)
    predicted_consumed = max(consumed_before - max(int(replaced_kcal or 0), 0), 0) + max(int(estimated_kcal or 0), 0)
    predicted_remaining = budget_kcal - predicted_consumed
    return {
        "budget_kcal": budget_kcal,
        "consumed_kcal_before": consumed_before,
        "replaced_kcal_before": max(int(replaced_kcal or 0), 0),
        "predicted_consumed_kcal_after": predicted_consumed,
        "predicted_remaining_kcal_after": predicted_remaining,
        "overshoot_detected": predicted_remaining < 0,
        "overshoot_kcal": abs(min(predicted_remaining, 0)),
    }
