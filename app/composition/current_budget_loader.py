from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.domain import CurrentBudgetMealSummary, CurrentBudgetView
from app.budget.infrastructure.models import DayBudgetLedgerRecord
from app.intake.infrastructure.models import MealThreadRecord, MealVersionRecord
from app.runtime.application.execution_guard import evaluate_macro_display


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
            manager_intent=version.manager_intent,
            source_request_id=version.source_request_id,
        )
        for thread, version in meal_rows
    ]
    consumed_protein = sum(int(version.protein_g or 0) for _, version in meal_rows)
    consumed_carbs = sum(int(version.carb_g or 0) for _, version in meal_rows)
    consumed_fat = sum(int(version.fat_g or 0) for _, version in meal_rows)
    macro_guard = evaluate_macro_display(
        estimated_kcal=ledger.consumed_kcal if ledger is not None else 0,
        protein_g=consumed_protein,
        carb_g=consumed_carbs,
        fat_g=consumed_fat,
    )

    return CurrentBudgetView(
        user_id=user_id,
        local_date=local_date,
        budget_kcal=ledger.budget_kcal if ledger is not None else 0,
        consumed_kcal=ledger.consumed_kcal if ledger is not None else 0,
        consumed_protein=consumed_protein,
        consumed_carbs=consumed_carbs,
        consumed_fat=consumed_fat,
        show_macro=macro_guard.display_status == "show",
        macro_guard_reason=macro_guard.guard_reason,
        adjustment_kcal=ledger.adjustment_kcal if ledger is not None else 0,
        remaining_kcal=ledger.remaining_kcal if ledger is not None else 0,
        active_meal_count=len(meals),
        meals=meals,
        last_recomputed_at=ledger.last_recomputed_at if ledger is not None else None,
    )
