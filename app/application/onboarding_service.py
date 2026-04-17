from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from ..domain import ActiveBodyPlanView, BodyProfile, CurrentBudgetView
from ..models import User
from ..application.active_body_plan_read_model import build_active_body_plan_view
from ..application.current_budget_read_model import build_current_budget_view
from ..application.target_calculation import TargetCalculationInputs, TargetCalculationResult, calculate_recommended_target_kcal
from ..infrastructure.body_plan_persistence import (
    BodyPlanBootstrapWriteInput,
    BodyProfileUpsertInput,
    upsert_active_body_plan_from_bootstrap,
    upsert_active_body_profile,
)
from ..infrastructure.canonical_persistence import recompute_day_budget_ledger

GoalType = Literal["lose_weight", "maintain", "gain_weight"]
ProfileSex = Literal["female", "male"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]

_SAFETY_FLOOR_BY_SEX: dict[ProfileSex, int] = {
    "female": 1200,
    "male": 1500,
}


@dataclass(frozen=True)
class OnboardingBootstrapInput:
    sex: ProfileSex
    age_years: int
    height_cm: float
    current_weight_kg: float
    activity_level: ActivityLevel
    goal_type: GoalType = "lose_weight"
    local_date: str = ""
    weekly_target_rate_kg: float = 0.5
    target_weight_kg: float | None = None
    timezone: str | None = None


@dataclass(frozen=True)
class OnboardingBootstrapResult:
    body_profile: BodyProfile
    active_body_plan_view: ActiveBodyPlanView
    current_budget_view: CurrentBudgetView
    target_result: TargetCalculationResult
    rescue_trigger_enabled: bool


def _resolve_loss_target_kg_per_week(goal_type: GoalType, weekly_target_rate_kg: float) -> float:
    if goal_type == "lose_weight":
        return max(0.0, float(weekly_target_rate_kg))
    return 0.0


def _body_profile_from_record(record: object) -> BodyProfile:
    return BodyProfile(
        body_profile_id=getattr(record, "id", None),
        user_id=getattr(record, "user_id", None),
        profile_status=getattr(record, "profile_status", "active"),
        sex=getattr(record, "sex", "female"),
        age_years=getattr(record, "age_years", 0),
        height_cm=float(getattr(record, "height_cm", 0.0) or 0.0),
        current_weight_kg=float(getattr(record, "current_weight_kg", 0.0) or 0.0),
        activity_level=getattr(record, "activity_level", "sedentary"),
        goal_type=getattr(record, "goal_type", "lose_weight"),
        target_weight_kg=getattr(record, "target_weight_kg", None),
        weekly_target_rate_kg=getattr(record, "weekly_target_rate_kg", None),
        timezone=getattr(record, "timezone", None),
        metadata=dict(getattr(record, "metadata_json", {}) or {}),
        created_at=getattr(record, "created_at", None),
        updated_at=getattr(record, "updated_at", None),
    )


def bootstrap_body_plan_for_date(
    db: Session,
    *,
    user: User,
    inputs: OnboardingBootstrapInput,
) -> OnboardingBootstrapResult:
    if not isinstance(inputs.local_date, str) or not inputs.local_date.strip():
        raise ValueError("local_date is required for onboarding bootstrap")

    safety_floor_kcal = _SAFETY_FLOOR_BY_SEX[inputs.sex]
    effective_weekly_loss_target = _resolve_loss_target_kg_per_week(inputs.goal_type, inputs.weekly_target_rate_kg)
    target_result = calculate_recommended_target_kcal(
        inputs=TargetCalculationInputs(
            age_years=inputs.age_years,
            sex=inputs.sex,
            height_cm=inputs.height_cm,
            weight_kg=inputs.current_weight_kg,
            activity_level=inputs.activity_level,
            weekly_loss_target_kg=effective_weekly_loss_target,
            safety_floor_kcal=safety_floor_kcal,
        )
    )

    profile_record = upsert_active_body_profile(
        db,
        user=user,
        profile=BodyProfileUpsertInput(
            sex=inputs.sex,
            age_years=inputs.age_years,
            height_cm=inputs.height_cm,
            current_weight_kg=inputs.current_weight_kg,
            activity_level=inputs.activity_level,
            goal_type=inputs.goal_type,
            weekly_target_rate_kg=effective_weekly_loss_target if inputs.goal_type == "lose_weight" else 0.0,
            target_weight_kg=inputs.target_weight_kg,
            timezone=inputs.timezone,
        ),
    )

    upsert_active_body_plan_from_bootstrap(
        db,
        user=user,
        plan=BodyPlanBootstrapWriteInput(
            estimated_tdee_kcal=target_result.estimated_tdee_kcal,
            daily_budget_kcal=target_result.recommended_target_kcal,
            recommended_target_kcal=target_result.recommended_target_kcal,
            safety_floor_kcal=target_result.safety_floor_kcal,
            target_pace_kg_per_week=effective_weekly_loss_target if inputs.goal_type == "lose_weight" else 0.0,
            goal_type=inputs.goal_type,
        ),
    )
    db.commit()

    recompute_day_budget_ledger(
        db,
        user_id=user.id,
        local_date=inputs.local_date.strip(),
        budget_kcal=target_result.recommended_target_kcal,
    )

    return OnboardingBootstrapResult(
        body_profile=_body_profile_from_record(profile_record),
        active_body_plan_view=build_active_body_plan_view(db, user_id=user.id),
        current_budget_view=build_current_budget_view(db, user_id=user.id, local_date=inputs.local_date.strip()),
        target_result=target_result,
        rescue_trigger_enabled=inputs.goal_type != "gain_weight",
    )
