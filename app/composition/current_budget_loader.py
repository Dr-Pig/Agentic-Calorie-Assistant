from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.domain import CurrentBudgetMealSummary, CurrentBudgetView
from app.body.infrastructure.models import BodyPlanRecord
from app.budget.infrastructure.models import DayBudgetLedgerRecord
from app.intake.infrastructure.models import MealThreadRecord, MealVersionRecord
from app.runtime.application.execution_guard import evaluate_macro_display


def _active_plan_budget_kcal(db: Session, *, user_id: int) -> int:
    active_plan = db.execute(
        select(BodyPlanRecord.daily_budget_kcal).where(
            BodyPlanRecord.user_id == user_id,
            BodyPlanRecord.plan_status == "active",
            BodyPlanRecord.daily_budget_kcal > 0,
        )
    ).scalars().first()
    return int(active_plan or 0)


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
    active_consumed_kcal = sum(int(version.total_kcal or 0) for _, version in meal_rows)
    budget_kcal = int(ledger.budget_kcal or 0) if ledger is not None else _active_plan_budget_kcal(db, user_id=user_id)
    adjustment_kcal = int(ledger.adjustment_kcal or 0) if ledger is not None else 0
    consumed_kcal = active_consumed_kcal
    remaining_kcal = budget_kcal - consumed_kcal - adjustment_kcal
    macro_guard = evaluate_macro_display(
        estimated_kcal=consumed_kcal,
        protein_g=consumed_protein,
        carb_g=consumed_carbs,
        fat_g=consumed_fat,
    )

    return CurrentBudgetView(
        user_id=user_id,
        local_date=local_date,
        budget_kcal=budget_kcal,
        consumed_kcal=consumed_kcal,
        consumed_protein=consumed_protein,
        consumed_carbs=consumed_carbs,
        consumed_fat=consumed_fat,
        show_macro=macro_guard.display_status == "show",
        macro_guard_reason=macro_guard.guard_reason,
        adjustment_kcal=adjustment_kcal,
        remaining_kcal=remaining_kcal,
        active_meal_count=len(meals),
        meals=meals,
        last_recomputed_at=ledger.last_recomputed_at if ledger is not None else None,
    )
