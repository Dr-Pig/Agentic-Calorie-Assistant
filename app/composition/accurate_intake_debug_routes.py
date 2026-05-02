from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.budget.interface.today_surface import resolve_today_local_date
from app.composition.accurate_intake_debug_read_model import build_accurate_intake_debug_read_model
from app.composition.current_budget_read_model import build_current_budget_view
from app.database import get_db
from app.intake.interface.accurate_intake_debug_surface import render_accurate_intake_debug_surface
from app.shared.infra.models import User

router = APIRouter()

_NOT_CLAIMING = [
    "product_ready",
    "rollout_ready",
    "live_llm_ready",
    "web_ready",
    "production_db_ready",
]


def build_accurate_intake_debug_payload(
    db: Any,
    *,
    user_external_id: str,
    local_date: str | None,
) -> dict[str, Any]:
    resolved_local_date = resolve_today_local_date(local_date)
    user = db.query(User).filter(User.user_id == user_external_id).first()
    if user is None:
        return {
            "surface_id": "accurate_intake_debug_surface_v1",
            "read_only": True,
            "state_posture": "no_user",
            "user_external_id": user_external_id,
            "user_id": None,
            "local_date": resolved_local_date,
            "not_claiming": list(_NOT_CLAIMING),
            "model": {
                "today_summary": {
                    "source_kind": "no_user",
                    "read_only": True,
                    "local_date": resolved_local_date,
                    "budget_kcal": 0,
                    "consumed_kcal": 0,
                    "remaining_kcal": 0,
                    "active_meal_count": 0,
                },
                "meal_threads": [],
                "pending_drafts": [],
                "correction_history": [],
                "ledger_audit_events": [],
                "same_truth": {
                    "status": "not_applicable",
                    "source_truth": "no_user",
                    "debug_model_consumed_kcal": 0,
                    "current_budget_consumed_kcal": 0,
                },
            },
        }
    current_budget = build_current_budget_view(db, user_id=user.id, local_date=resolved_local_date)
    return {
        "surface_id": "accurate_intake_debug_surface_v1",
        "read_only": True,
        "state_posture": "canonical_user_state",
        "user_external_id": user_external_id,
        "user_id": user.id,
        "local_date": resolved_local_date,
        "not_claiming": list(_NOT_CLAIMING),
        "model": build_accurate_intake_debug_read_model(
            db,
            user_id=user.id,
            local_date=resolved_local_date,
            current_budget=current_budget,
        ),
    }


@router.get("/accurate-intake/debug")
async def accurate_intake_debug(
    user_id: str = "default_user",
    local_date: str | None = None,
    db: Any = Depends(get_db),
) -> dict[str, Any]:
    return build_accurate_intake_debug_payload(db, user_external_id=user_id, local_date=local_date)


@router.get("/accurate-intake/debug/surface", response_class=HTMLResponse)
async def accurate_intake_debug_surface(
    user_id: str = "default_user",
    local_date: str | None = None,
    db: Any = Depends(get_db),
) -> HTMLResponse:
    payload = build_accurate_intake_debug_payload(db, user_external_id=user_id, local_date=local_date)
    return HTMLResponse(
        content=render_accurate_intake_debug_surface(payload),
        media_type="text/html; charset=utf-8",
    )
