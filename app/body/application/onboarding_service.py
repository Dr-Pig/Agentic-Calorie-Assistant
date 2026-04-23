from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from ...shared.domain import ActiveBodyPlanView, BodyProfile, CurrentBudgetView
from ...models import User
from .active_body_plan_read_model import build_active_body_plan_view
from ...budget.application.current_budget_read_model import build_current_budget_view
from .target_calculation import TargetCalculationInputs, TargetCalculationResult, calculate_recommended_target_kcal
from ..infrastructure.body_plan_persistence import (
    BodyPlanBootstrapWriteInput,
    BodyProfileUpsertInput,
    upsert_active_body_plan_from_bootstrap,
    upsert_active_body_profile,
)
from app.shared.infra.canonical_persistence import recompute_day_budget_ledger

GoalType = Literal["lose_weight", "maintain", "gain_weight"]
ProfileSex = Literal["female", "male"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]
DailyLifestyle = Literal[
    "mostly_sedentary",
    "sedentary_with_some_walking",
    "on_feet_often",
    "physically_demanding",
]
WeeklyExerciseDaysBand = Literal["0", "1_2", "3_4", "5_plus"]

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
    activity_level: ActivityLevel = "sedentary"
    goal_type: GoalType = "lose_weight"
    local_date: str = ""
    weekly_target_rate_kg: float = 0.5
    target_weight_kg: float | None = None
    timezone: str | None = None
    daily_lifestyle: DailyLifestyle | None = None
    weekly_exercise_days_band: WeeklyExerciseDaysBand | None = None


_LIFESTYLE_BASE_MULTIPLIER: dict[DailyLifestyle, float] = {
    "mostly_sedentary": 1.20,
    "sedentary_with_some_walking": 1.27,
    "on_feet_often": 1.35,
    "physically_demanding": 1.45,
}

_WEEKLY_EXERCISE_BONUS: dict[WeeklyExerciseDaysBand, float] = {
    "0": 0.00,
    "1_2": 0.03,
    "3_4": 0.06,
    "5_plus": 0.10,
}

_LEGACY_ACTIVITY_FALLBACK: dict[ActivityLevel, float] = {
    "sedentary": 1.20,
    "light": 1.27,
    "moderate": 1.35,
    "active": 1.45,
    "very_active": 1.55,
}


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


def _resolved_activity_policy(inputs: OnboardingBootstrapInput) -> tuple[float, ActivityLevel, dict[str, object]]:
    if inputs.daily_lifestyle is not None or inputs.weekly_exercise_days_band is not None:
        lifestyle = inputs.daily_lifestyle or "mostly_sedentary"
        weekly_band = inputs.weekly_exercise_days_band or "0"
        base_multiplier = _LIFESTYLE_BASE_MULTIPLIER[lifestyle]
        exercise_bonus = _WEEKLY_EXERCISE_BONUS[weekly_band]
        resolved_multiplier = min(1.55, round(base_multiplier + exercise_bonus, 3))
        if resolved_multiplier <= 1.24:
            coarse_level: ActivityLevel = "sedentary"
        elif resolved_multiplier <= 1.33:
            coarse_level = "light"
        elif resolved_multiplier <= 1.43:
            coarse_level = "moderate"
        elif resolved_multiplier <= 1.50:
            coarse_level = "active"
        else:
            coarse_level = "very_active"
        return (
            resolved_multiplier,
            coarse_level,
            {
                "activity_policy_version": "bundle1_conservative_v1",
                "daily_lifestyle": lifestyle,
                "weekly_exercise_days_band": weekly_band,
                "base_multiplier": base_multiplier,
                "exercise_bonus": exercise_bonus,
                "resolved_activity_multiplier": resolved_multiplier,
            },
        )

    resolved_multiplier = _LEGACY_ACTIVITY_FALLBACK[inputs.activity_level]
    return (
        resolved_multiplier,
        inputs.activity_level,
        {
            "activity_policy_version": "legacy_activity_level_v1",
            "legacy_activity_level": inputs.activity_level,
            "resolved_activity_multiplier": resolved_multiplier,
        },
    )


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
    resolved_activity_multiplier, persisted_activity_level, activity_policy_metadata = _resolved_activity_policy(inputs)
    target_result = calculate_recommended_target_kcal(
        inputs=TargetCalculationInputs(
            age_years=inputs.age_years,
            sex=inputs.sex,
            height_cm=inputs.height_cm,
            weight_kg=inputs.current_weight_kg,
            activity_level=persisted_activity_level,
            weekly_loss_target_kg=effective_weekly_loss_target,
            safety_floor_kcal=safety_floor_kcal,
            activity_multiplier_override=resolved_activity_multiplier,
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
            activity_level=persisted_activity_level,
            goal_type=inputs.goal_type,
            weekly_target_rate_kg=effective_weekly_loss_target if inputs.goal_type == "lose_weight" else 0.0,
            target_weight_kg=inputs.target_weight_kg,
            timezone=inputs.timezone,
            metadata=activity_policy_metadata,
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
            metadata=activity_policy_metadata,
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
