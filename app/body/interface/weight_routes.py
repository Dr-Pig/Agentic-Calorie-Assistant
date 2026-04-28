from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from pydantic import BaseModel
from ...intake.application.canonical_commit_bridge import load_body_observation_history, record_body_observation_to_canonical, get_active_body_profile_record
from ...database import get_db, get_or_create_user
from .weight_surface import render_weight_surface
from ..application import bootstrap_body_plan_for_date, OnboardingBootstrapInput

router = APIRouter()

class WeightObservationRequest(BaseModel):
    user_id: str
    weight_kg: float
    local_date: str



def _load_weight_history(
    db: Any,
    *,
    user_id: str,
    local_date: str | None,
) -> tuple[int, str | None, list[BodyObservation]]:
    user = get_or_create_user(db, user_id)
    resolved_local_date = None
    if isinstance(local_date, str) and local_date.strip():
        resolved_local_date = local_date.strip()
    history = load_body_observation_history(
        db,
        user_id=user.id,
        local_date=resolved_local_date,
    )
    return user.id, resolved_local_date, history


@router.get("/weight/observations")
async def weight_observations(
    user_id: str = "default_user",
    local_date: str | None = None,
    db: Any = Depends(get_db),
) -> dict:
    resolved_user_id, resolved_local_date, observations = _load_weight_history(
        db,
        user_id=user_id,
        local_date=local_date,
    )
    return {
        "user_id": resolved_user_id,
        "local_date": resolved_local_date,
        "observations": [observation.model_dump(mode="json") for observation in observations],
    }


@router.get("/weight", response_class=HTMLResponse)
async def weight(
    user_id: str = "default_user",
    local_date: str | None = None,
    db: Any = Depends(get_db),
) -> HTMLResponse:
    _, resolved_local_date, observations = _load_weight_history(
        db,
        user_id=user_id,
        local_date=local_date,
    )
    return HTMLResponse(
        content=render_weight_surface(user_id=user_id, local_date=resolved_local_date, observations=observations),
        media_type="text/html; charset=utf-8",
    )

@router.post("/weight/observation")
async def post_weight_observation(req: WeightObservationRequest, db: Any = Depends(get_db)) -> dict:
    user = get_or_create_user(db, req.user_id)
    # Save the new weight
    obs = record_body_observation_to_canonical(
        db,
        user=user,
        value=req.weight_kg,
        unit="kg",
        observation_type="weight",
        local_date=req.local_date
    )
    
    # Re-bootstrap plan if a plan already exists, carrying over settings
    recomputed_target = None
    profile = get_active_body_profile_record(db, user_id=user.id)
    if profile:
        profile_meta = dict(profile.metadata_json or {})
        inputs = OnboardingBootstrapInput(
            sex=profile.sex,
            age_years=profile.age_years,
            height_cm=profile.height_cm,
            current_weight_kg=req.weight_kg,
            activity_level=profile.activity_level,
            goal_type=profile.goal_type,
            weekly_target_rate_kg=profile_meta.get("weekly_target_rate_kg", 0.5),  # type: ignore
            local_date=req.local_date,
            timezone="UTC"
        )
        result = bootstrap_body_plan_for_date(db, user=user, inputs=inputs)
        if isinstance(result, dict):
            recomputed_target = result.get("recommended_target_kcal")

    return {
        "status": "ok",
        "observation_id": obs.observation_id,
        "weight_kg": req.weight_kg,
        "recomputed_target_kcal": recomputed_target,
    }
