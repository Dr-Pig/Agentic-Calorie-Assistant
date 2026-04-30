from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from pydantic import BaseModel
from app.body.application.body_observation_service import load_body_observation_history, record_body_observation_to_canonical
from app.body.interface.weight_surface import render_weight_surface
from app.database import get_db, get_or_create_user

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
    obs = record_body_observation_to_canonical(
        db,
        user=user,
        value=req.weight_kg,
        unit="kg",
        observation_type="weight",
        local_date=req.local_date
    )

    return {
        "status": "ok",
        "observation_id": obs.observation_id,
        "weight_kg": req.weight_kg,
        "recomputed_target_kcal": None,
    }
