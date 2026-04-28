from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from pydantic import BaseModel
from ..application import build_current_budget_view
from ...intake.application.canonical_commit_bridge import record_budget_adjustment_to_canonical
from ...database import get_db, get_or_create_user
from .today_surface import render_today_surface, resolve_today_local_date

router = APIRouter()

class BudgetAdjustmentRequest(BaseModel):
    user_id: str
    delta_kcal: int
    local_date: str



def _load_today_budget_view(
    db: Any,
    *,
    user_id: str,
    local_date: str | None,
) -> Any:
    user = get_or_create_user(db, user_id)
    return build_current_budget_view(
        db,
        user_id=user.id,
        local_date=resolve_today_local_date(local_date),
    )
@router.get("/today/current-budget")
async def today_current_budget(
    user_id: str = "default_user",
    local_date: str | None = None,
    db: Any = Depends(get_db),
) -> dict:
    view = _load_today_budget_view(db, user_id=user_id, local_date=local_date)
    return view.model_dump(mode="json")


@router.get("/today", response_class=HTMLResponse)
async def today(
    user_id: str = "default_user",
    local_date: str | None = None,
    db: Any = Depends(get_db),
) -> HTMLResponse:
    resolved_local_date = resolve_today_local_date(local_date)
    view = _load_today_budget_view(db, user_id=user_id, local_date=resolved_local_date)
    return HTMLResponse(
        content=render_today_surface(user_id=user_id, local_date=resolved_local_date, view=view),
        media_type="text/html; charset=utf-8",
    )

@router.post("/today/budget-adjustment")
async def post_budget_adjustment(req: BudgetAdjustmentRequest, db: Any = Depends(get_db)) -> dict:
    user = get_or_create_user(db, req.user_id)
    entry = record_budget_adjustment_to_canonical(
        db,
        user=user,
        delta_kcal=req.delta_kcal,
        local_date=req.local_date,
        metadata={"source": "ui_adjustment"}
    )
    return {
        "status": "ok",
        "ledger_entry_id": entry.id,
        "delta_kcal": req.delta_kcal,
    }
