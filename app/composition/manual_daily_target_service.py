from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.body.application import build_active_body_plan_view
from app.body.infrastructure.body_plan_persistence import (
    BodyPlanBootstrapWriteInput,
    load_active_body_plan_record,
    upsert_active_body_plan_from_bootstrap,
)
from app.composition.canonical_persistence import recompute_day_budget_ledger
from app.composition.current_budget_read_model import build_current_budget_view
from app.shared.domain import ActiveBodyPlanView, CurrentBudgetView
from app.shared.infra.models import User

ManualDailyTargetSource = Literal["user_chat", "user_ui", "system_default"]


@dataclass(frozen=True)
class ManualDailyTargetInput:
    daily_target_kcal: int
    local_date: str
    source: ManualDailyTargetSource = "user_chat"


@dataclass(frozen=True)
class ManualDailyTargetResult:
    status: str
    user_id: int
    local_date: str
    previous_daily_target_kcal: int | None
    target_delta_kcal: int | None
    active_body_plan_view: ActiveBodyPlanView
    current_budget_view: CurrentBudgetView
    live_llm_invoked: bool = False
    product_readiness_claimed: bool = False
    private_self_use_approved: bool = False
    production_selected: bool = False


def set_manual_daily_target(
    db: Session,
    *,
    user: User,
    inputs: ManualDailyTargetInput,
) -> ManualDailyTargetResult:
    local_date = inputs.local_date.strip()
    if not local_date:
        raise ValueError("local_date_required")
    if inputs.daily_target_kcal < 800 or inputs.daily_target_kcal > 5000:
        raise ValueError("manual_daily_target_out_of_bounds")

    active_plan = load_active_body_plan_record(db, user_id=user.id)
    previous_target = int(active_plan.daily_budget_kcal) if active_plan is not None else None
    metadata = dict(active_plan.metadata_json or {}) if active_plan is not None else {}
    goal_type = str(metadata.get("goal_type") or "lose_weight")

    upsert_active_body_plan_from_bootstrap(
        db,
        user=user,
        plan=BodyPlanBootstrapWriteInput(
            estimated_tdee_kcal=(
                int(active_plan.estimated_tdee or inputs.daily_target_kcal)
                if active_plan is not None
                else inputs.daily_target_kcal
            ),
            daily_budget_kcal=inputs.daily_target_kcal,
            safety_floor_kcal=int(active_plan.safety_floor_kcal or 0) if active_plan is not None else 0,
            target_pace_kg_per_week=(
                float(active_plan.target_pace_kg_per_week)
                if active_plan is not None and active_plan.target_pace_kg_per_week is not None
                else None
            ),
            goal_type=goal_type if goal_type in {"lose_weight", "maintain", "gain_weight"} else "lose_weight",
            plan_source="manual_daily_target",
            recommended_target_kcal=inputs.daily_target_kcal,
            metadata={
                "manual_target_source": inputs.source,
                "manual_target_local_date": local_date,
            },
        ),
    )
    db.flush()

    recompute_day_budget_ledger(
        db,
        user_id=user.id,
        local_date=local_date,
        budget_kcal=inputs.daily_target_kcal,
    )

    active_body_plan_view = build_active_body_plan_view(db, user_id=user.id)
    current_budget_view = build_current_budget_view(db, user_id=user.id, local_date=local_date)
    return ManualDailyTargetResult(
        status="ok",
        user_id=user.id,
        local_date=local_date,
        previous_daily_target_kcal=previous_target,
        target_delta_kcal=(
            inputs.daily_target_kcal - previous_target if previous_target is not None else None
        ),
        active_body_plan_view=active_body_plan_view,
        current_budget_view=current_budget_view,
    )
