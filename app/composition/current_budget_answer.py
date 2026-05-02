from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.body.application.active_body_plan_read_model import build_active_body_plan_view
from app.shared.domain import ActiveBodyPlanView, CurrentBudgetView
from .current_budget_read_model import build_current_budget_view

BudgetAnswerStatus = Literal["ready", "onboarding_required"]


@dataclass(frozen=True)
class RemainingBudgetAnswerContract:
    status: BudgetAnswerStatus
    user_id: int
    local_date: str
    daily_target_kcal: int | None
    consumed_kcal: int
    remaining_kcal: int | None
    meal_count: int


def _view_field(view: object, field_name: str, default: object = None) -> object:
    if hasattr(view, field_name):
        return getattr(view, field_name)
    if hasattr(view, "model_dump"):
        try:
            payload = view.model_dump(mode="json")
        except TypeError:
            payload = view.model_dump()
        if isinstance(payload, dict):
            return payload.get(field_name, default)
    return default


def build_remaining_budget_answer_contract(
    db: Session,
    *,
    user_id: int,
    local_date: str,
) -> RemainingBudgetAnswerContract:
    current_budget = build_current_budget_view(db, user_id=user_id, local_date=local_date)
    active_plan = build_active_body_plan_view(db, user_id=user_id)
    return build_remaining_budget_answer_contract_from_views(
        current_budget=current_budget,
        active_plan=active_plan,
    )


def build_remaining_budget_answer_contract_from_views(
    *,
    current_budget: CurrentBudgetView,
    active_plan: ActiveBodyPlanView,
) -> RemainingBudgetAnswerContract:
    user_id = int(_view_field(current_budget, "user_id", 0) or 0)
    local_date = str(_view_field(current_budget, "local_date", "") or "")
    consumed_kcal = int(_view_field(current_budget, "consumed_kcal", 0) or 0)
    remaining_kcal = int(_view_field(current_budget, "remaining_kcal", 0) or 0)
    meal_count = int(_view_field(current_budget, "active_meal_count", 0) or 0)
    if _view_field(active_plan, "body_plan_id") is None:
        return RemainingBudgetAnswerContract(
            status="onboarding_required",
            user_id=user_id,
            local_date=local_date,
            daily_target_kcal=None,
            consumed_kcal=consumed_kcal,
            remaining_kcal=None,
            meal_count=meal_count,
        )

    return RemainingBudgetAnswerContract(
        status="ready",
        user_id=user_id,
        local_date=local_date,
        daily_target_kcal=int(_view_field(current_budget, "budget_kcal", 0) or 0),
        consumed_kcal=consumed_kcal,
        remaining_kcal=remaining_kcal,
        meal_count=meal_count,
    )
