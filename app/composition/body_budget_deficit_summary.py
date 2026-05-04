from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.body.application import build_active_body_plan_view
from app.body.application.body_observation_service import (
    get_latest_weight_observation,
    load_body_observation_history,
)
from app.budget.infrastructure.models import DayBudgetLedgerRecord
from app.composition.current_budget_read_model import build_current_budget_view
from app.shared.domain import ActiveBodyPlanView, CurrentBudgetView


def _model_payload(model: Any | None) -> dict[str, Any] | None:
    if model is None:
        return None
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return dict(model)


def _has_day_budget_ledger(db: Session, *, user_id: int, local_date: str) -> bool:
    return (
        db.execute(
            select(DayBudgetLedgerRecord.id).where(
                DayBudgetLedgerRecord.user_id == user_id,
                DayBudgetLedgerRecord.local_date == local_date,
            )
        ).scalar_one_or_none()
        is not None
    )


def _active_target(
    *,
    current_budget: CurrentBudgetView,
    active_plan: ActiveBodyPlanView,
    has_day_budget_ledger: bool,
) -> tuple[int | None, str]:
    if has_day_budget_ledger and int(current_budget.budget_kcal or 0) > 0:
        return int(current_budget.budget_kcal), "day_budget_ledger"
    if active_plan.body_plan_id is not None and int(active_plan.daily_budget_kcal or 0) > 0:
        return int(active_plan.daily_budget_kcal), "active_body_plan"
    if active_plan.body_plan_id is not None and int(active_plan.recommended_target_kcal or 0) > 0:
        return int(active_plan.recommended_target_kcal), "active_body_plan_recommended"
    return None, "unavailable"


def _estimated_daily_deficit(
    *,
    active_plan: ActiveBodyPlanView,
    active_daily_target_kcal: int | None,
) -> int | None:
    if active_plan.body_plan_id is None or active_daily_target_kcal is None:
        return None
    if int(active_plan.daily_deficit_kcal or 0) > 0:
        return int(active_plan.daily_deficit_kcal)
    if int(active_plan.estimated_tdee or 0) <= 0:
        return None
    return max(0, int(active_plan.estimated_tdee) - active_daily_target_kcal)


def build_body_budget_deficit_summary(
    db: Session,
    *,
    user_id: int,
    local_date: str,
) -> dict[str, Any]:
    current_budget = build_current_budget_view(db, user_id=user_id, local_date=local_date)
    active_plan = build_active_body_plan_view(db, user_id=user_id)
    has_ledger = _has_day_budget_ledger(db, user_id=user_id, local_date=local_date)
    active_target, target_source = _active_target(
        current_budget=current_budget,
        active_plan=active_plan,
        has_day_budget_ledger=has_ledger,
    )
    consumed_kcal = int(current_budget.consumed_kcal or 0)
    adjustment_kcal = int(current_budget.adjustment_kcal or 0) if has_ledger else 0
    remaining_kcal = (
        int(current_budget.remaining_kcal)
        if has_ledger and active_target is not None
        else active_target - consumed_kcal - adjustment_kcal
        if active_target is not None
        else None
    )
    latest_weight = get_latest_weight_observation(db, user_id=user_id)
    weight_history = load_body_observation_history(db, user_id=user_id, observation_type="weight")

    return {
        "source_kind": "body_budget_deficit_summary",
        "read_only": True,
        "truth_owner": "composition_body_budget_read_model",
        "user_id": user_id,
        "local_date": local_date,
        "target_available": active_target is not None,
        "remaining_available": remaining_kcal is not None,
        "target_source": target_source,
        "current_budget_ledger_present": has_ledger,
        "active_daily_target_kcal": active_target,
        "recommended_target_kcal": (
            int(active_plan.recommended_target_kcal)
            if active_plan.body_plan_id is not None and int(active_plan.recommended_target_kcal or 0) > 0
            else None
        ),
        "consumed_kcal": consumed_kcal,
        "adjustment_kcal": adjustment_kcal,
        "remaining_kcal": remaining_kcal,
        "estimated_daily_deficit_kcal": _estimated_daily_deficit(
            active_plan=active_plan,
            active_daily_target_kcal=active_target,
        ),
        "latest_weight_kg": float(latest_weight.value) if latest_weight is not None else None,
        "latest_weight_observed_at": (
            latest_weight.observed_at.isoformat() if latest_weight is not None and latest_weight.observed_at else None
        ),
        "latest_weight_observation_id": latest_weight.observation_id if latest_weight is not None else None,
        "latest_weight_source": "body_observation" if latest_weight is not None else None,
        "weight_history_count": len(weight_history),
        "body_profile_current_weight_kg": active_plan.current_weight_kg,
        "body_profile_current_weight_role": "onboarding_profile_baseline",
        "current_budget": _model_payload(current_budget),
        "active_body_plan": _model_payload(active_plan),
        "latest_weight_observation": _model_payload(latest_weight),
        "automatic_calibration_enabled": False,
        "rescue_enabled": False,
        "recommendation_enabled": False,
        "proactive_enabled": False,
        "live_tool_calling": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
    }


__all__ = ["build_body_budget_deficit_summary"]
