from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain import CurrentBudgetMealSummary, CurrentBudgetView
from ..models import DayBudgetLedgerRecord, MealThreadRecord, MealVersionRecord


def load_current_budget_view(
    db: Session,
    *,
    user_id: int,
    local_date: str,
) -> CurrentBudgetView:
    ledger = db.execute(
        select(DayBudgetLedgerRecord).where(
            DayBudgetLedgerRecord.user_id == user_id,
            DayBudgetLedgerRecord.local_date == local_date,
        )
    ).scalar_one_or_none()

    meal_rows = db.execute(
        select(MealThreadRecord, MealVersionRecord)
        .join(MealVersionRecord, MealThreadRecord.active_version_id == MealVersionRecord.id)
        .where(
            MealThreadRecord.user_id == user_id,
            MealVersionRecord.local_date == local_date,
            MealVersionRecord.version_status == "active",
            MealVersionRecord.resolution_status == "completed_meal",
        )
        .order_by(MealVersionRecord.occurred_at.asc(), MealVersionRecord.id.asc())
    ).all()

    meals = [
        CurrentBudgetMealSummary(
            meal_thread_id=thread.id,
            meal_version_id=version.id,
            meal_title=version.meal_title or thread.title,
            total_kcal=version.total_kcal,
            occurred_at=version.occurred_at,
            resolution_status=version.resolution_status,
            planner_intent=version.planner_intent,
        )
        for thread, version in meal_rows
    ]

    return CurrentBudgetView(
        user_id=user_id,
        local_date=local_date,
        budget_kcal=ledger.budget_kcal if ledger is not None else 0,
        consumed_kcal=ledger.consumed_kcal if ledger is not None else 0,
        adjustment_kcal=ledger.adjustment_kcal if ledger is not None else 0,
        remaining_kcal=ledger.remaining_kcal if ledger is not None else 0,
        active_meal_count=len(meals),
        meals=meals,
        last_recomputed_at=ledger.last_recomputed_at if ledger is not None else None,
    )
