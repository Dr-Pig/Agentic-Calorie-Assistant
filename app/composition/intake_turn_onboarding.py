from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_or_create_user
from app.intake.application.intake_trace_tools import append_trace_event_tool
from app.intake.application.intake_turn_support import normalized_activity_level
from app.runtime.application.execution_guard import validate_onboarding_seed


@dataclass(frozen=True)
class IntakeOnboardingPayload:
    sex: str
    age_years: int
    height_cm: float
    current_weight_kg: float
    goal_type: str
    weekly_target_rate_kg: float
    timezone: str = "UTC"
    target_weight_kg: float | None = None
    activity_level: str | None = None
    daily_lifestyle: str | None = None
    weekly_exercise_days_band: str | None = None


def complete_onboarding_intake_turn(
    db: Session,
    *,
    user_external_id: str,
    onboarding_payload: Any,
    local_date: str,
    request_id: str,
) -> Any:
    if onboarding_payload is None:
        raise ValueError("Structured onboarding payload is required for complete_onboarding.")
    user = get_or_create_user(db, user_external_id)
    onboarding_result = bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex=onboarding_payload.sex,
            age_years=onboarding_payload.age_years,
            height_cm=onboarding_payload.height_cm,
            current_weight_kg=onboarding_payload.current_weight_kg,
            activity_level=normalized_activity_level(onboarding_payload.activity_level),
            daily_lifestyle=onboarding_payload.daily_lifestyle,
            weekly_exercise_days_band=onboarding_payload.weekly_exercise_days_band,
            goal_type=onboarding_payload.goal_type,
            weekly_target_rate_kg=onboarding_payload.weekly_target_rate_kg,
            target_weight_kg=onboarding_payload.target_weight_kg,
            local_date=local_date,
            timezone=onboarding_payload.timezone,
        ),
    )
    guard = validate_onboarding_seed(
        recommended_target_kcal=onboarding_result.target_result.recommended_target_kcal,
        safety_floor_kcal=onboarding_result.target_result.safety_floor_kcal,
    )
    if not guard.ok:
        raise ValueError(f"Intake onboarding guard failed: {', '.join(guard.violations)}")
    append_trace_event_tool(
        request_id=request_id,
        stage="v2_onboarding_seed",
        status="ok",
        summary={
            "daily_budget_kcal": onboarding_result.target_result.recommended_target_kcal,
            "estimated_tdee_kcal": onboarding_result.target_result.estimated_tdee_kcal,
            "safety_floor_kcal": onboarding_result.target_result.safety_floor_kcal,
        },
    )
    return onboarding_result


__all__ = ["IntakeOnboardingPayload", "complete_onboarding_intake_turn"]
