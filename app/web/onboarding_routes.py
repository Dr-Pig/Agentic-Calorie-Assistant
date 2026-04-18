from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..application.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from ..database import get_db, get_or_create_user

router = APIRouter()

class OnboardingRequest(BaseModel):
    user_id: str
    sex: str
    age_years: int
    height_cm: float
    current_weight_kg: float
    activity_level: str
    goal_type: str
    weekly_target_rate_kg: float
    local_date: str
    timezone: str = "UTC"

@router.post("/onboarding/bootstrap")
async def onboarding_bootstrap(req: OnboardingRequest, db: Any = Depends(get_db)) -> dict:
    user = get_or_create_user(db, req.user_id)
    inputs = OnboardingBootstrapInput(
        sex=req.sex, # type: ignore
        age_years=req.age_years,
        height_cm=req.height_cm,
        current_weight_kg=req.current_weight_kg,
        activity_level=req.activity_level, # type: ignore
        goal_type=req.goal_type, # type: ignore
        weekly_target_rate_kg=req.weekly_target_rate_kg,
        local_date=req.local_date,
        timezone=req.timezone,
    )
    result = bootstrap_body_plan_for_date(db, user=user, inputs=inputs)
    return {
        "status": "success",
        "target_kcal": result.target_result.recommended_target_kcal,
        "daily_deficit_kcal": result.target_result.daily_deficit_kcal,
        "active_body_plan": result.active_body_plan_view.model_dump(mode="json"),
        "current_budget": result.current_budget_view.model_dump(mode="json"),
    }
