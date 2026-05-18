from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.domain import CurrentBudgetMealSummary, CurrentBudgetView
from app.body.infrastructure.models import BodyPlanRecord
from app.budget.infrastructure.models import DayBudgetLedgerRecord
from app.intake.infrastructure.models import MealItemRecord, MealThreadRecord, MealVersionRecord
from app.composition.current_budget_macro_visibility import (
    build_day_macro_summary,
    build_meal_macro_summary,
)


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

    version_ids = [version.id for _, version in meal_rows]
    items_by_version = _items_by_version(db, version_ids=version_ids)
    meals: list[CurrentBudgetMealSummary] = []
    for thread, version in meal_rows:
        macro = build_meal_macro_summary(version, items_by_version.get(version.id, []))
        meals.append(
            CurrentBudgetMealSummary(
                meal_thread_id=thread.id,
                meal_version_id=version.id,
                meal_title=version.meal_title or thread.title,
                total_kcal=version.total_kcal,
                consumed_protein=macro["protein_g"],
                consumed_carbs=macro["carb_g"],
                consumed_fat=macro["fat_g"],
                macro_display_status=macro["display_status"],
                macro_guard_reason=macro["guard_reason"],
                macro_source_basis=macro["source_basis"],
                occurred_at=version.occurred_at,
                resolution_status=version.resolution_status,
                manager_intent=version.manager_intent,
                source_request_id=version.source_request_id,
            )
        )
    day_macro = build_day_macro_summary(meals)
    consumed_protein = day_macro["protein_g"]
    consumed_carbs = day_macro["carb_g"]
    consumed_fat = day_macro["fat_g"]
    active_consumed_kcal = sum(int(version.total_kcal or 0) for _, version in meal_rows)
    budget_kcal = int(ledger.budget_kcal or 0) if ledger is not None else _active_plan_budget_kcal(db, user_id=user_id)
    adjustment_kcal = int(ledger.adjustment_kcal or 0) if ledger is not None else 0
    consumed_kcal = active_consumed_kcal
    remaining_kcal = budget_kcal - consumed_kcal - adjustment_kcal
    return CurrentBudgetView(
        user_id=user_id,
        local_date=local_date,
        budget_kcal=budget_kcal,
        consumed_kcal=consumed_kcal,
        consumed_protein=consumed_protein,
        consumed_carbs=consumed_carbs,
        consumed_fat=consumed_fat,
        show_macro=day_macro["display_status"] in {"show", "partial"},
        macro_guard_reason=day_macro["guard_reason"],
        adjustment_kcal=adjustment_kcal,
        remaining_kcal=remaining_kcal,
        active_meal_count=len(meals),
        meals=meals,
        last_recomputed_at=ledger.last_recomputed_at if ledger is not None else None,
    )


def _items_by_version(db: Session, *, version_ids: list[int]) -> dict[int, list[MealItemRecord]]:
    if not version_ids:
        return {}
    rows = (
        db.execute(
            select(MealItemRecord)
            .where(MealItemRecord.meal_version_id.in_(version_ids))
            .order_by(MealItemRecord.meal_version_id.asc(), MealItemRecord.item_index.asc(), MealItemRecord.id.asc())
        )
        .scalars()
        .all()
    )
    grouped: dict[int, list[MealItemRecord]] = {}
    for row in rows:
        grouped.setdefault(int(row.meal_version_id), []).append(row)
    return grouped
