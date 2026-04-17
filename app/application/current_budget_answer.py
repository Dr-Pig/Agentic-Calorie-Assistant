from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from .active_body_plan_read_model import build_active_body_plan_view
from .current_budget_read_model import build_current_budget_view

BudgetAnswerStatus = Literal["ready", "onboarding_required"]


@dataclass(frozen=True)
class RemainingBudgetAnswerContract:
    status: BudgetAnswerStatus
    user_id: int
    local_date: str
    daily_target_kcal: int
    consumed_kcal: int
    remaining_kcal: int
    meal_count: int


def build_remaining_budget_answer_contract(
    db: Session,
    *,
    user_id: int,
    local_date: str,
) -> RemainingBudgetAnswerContract:
    current_budget = build_current_budget_view(db, user_id=user_id, local_date=local_date)
    active_plan = build_active_body_plan_view(db, user_id=user_id)

    if active_plan.body_plan_id is None:
        return RemainingBudgetAnswerContract(
            status="onboarding_required",
            user_id=user_id,
            local_date=local_date,
            daily_target_kcal=0,
            consumed_kcal=current_budget.consumed_kcal,
            remaining_kcal=current_budget.remaining_kcal,
            meal_count=current_budget.active_meal_count,
        )

    return RemainingBudgetAnswerContract(
        status="ready",
        user_id=user_id,
        local_date=local_date,
        daily_target_kcal=current_budget.budget_kcal,
        consumed_kcal=current_budget.consumed_kcal,
        remaining_kcal=current_budget.remaining_kcal,
        meal_count=current_budget.active_meal_count,
    )
