from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

from app.body.application.active_body_plan_read_model import build_active_body_plan_view
from app.budget.interface.today_surface import resolve_today_local_date
from app.composition.accurate_intake_chat_history_read_model import build_accurate_intake_chat_history_payload
from app.composition.accurate_intake_debug_read_model import build_accurate_intake_debug_read_model
from app.composition.current_budget_read_model import build_current_budget_view
from app.composition.dogfood_feedback_auto_context import (
    build_feedback_auto_context_from_backend,
)
from app.composition.dogfood_feedback_capture import build_feedback_record_from_route_payload
from app.composition.dogfood_review_queue import (
    append_desktop_feedback_record,
)
from app.composition.dogfood_review_queue_surface import (
    DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH,
    build_desktop_review_queue_response,
)
from app.composition.local_data_hygiene_routes import router as local_data_hygiene_router
from app.database import get_db
from app.intake.interface.accurate_intake_debug_surface import render_accurate_intake_debug_surface
from app.runtime.interface.local_debug_auth import (
    require_local_debug_access,
    set_local_debug_session_cookie,
    validate_local_debug_token,
)
from app.shared.infra.models import User

router = APIRouter()
router.include_router(local_data_hygiene_router)
DOGFOOD_FEEDBACK_DIR = Path("workspace_data/local_dogfood_feedback")

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
    active_plan = build_active_body_plan_view(db, user_id=user.id)
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
            active_plan=active_plan,
        ),
    }


@router.post("/accurate-intake/local-debug-session", status_code=204)
async def accurate_intake_local_debug_session(
    request: Request,
    payload: dict[str, Any] = Body(...),
) -> Response:
    token = validate_local_debug_token(request, str(payload.get("token") or ""))
    response = Response(status_code=204)
    set_local_debug_session_cookie(response, token)
    return response


@router.get("/accurate-intake/local-debug-session")
async def accurate_intake_local_debug_session_probe(
    _local_debug_access: None = Depends(require_local_debug_access),
) -> dict[str, Any]:
    return {"status": "connected", "local_only": True}


@router.get("/accurate-intake/debug")
async def accurate_intake_debug(
    user_id: str = "default_user",
    local_date: str | None = None,
    db: Any = Depends(get_db),
    _local_debug_access: None = Depends(require_local_debug_access),
) -> dict[str, Any]:
    return build_accurate_intake_debug_payload(db, user_external_id=user_id, local_date=local_date)


@router.get("/accurate-intake/chat-history")
async def accurate_intake_chat_history(
    user_id: str = "default_user",
    local_date: str | None = None,
    db: Any = Depends(get_db),
    _local_debug_access: None = Depends(require_local_debug_access),
) -> dict[str, Any]:
    return build_accurate_intake_chat_history_payload(db, user_external_id=user_id, local_date=local_date)


@router.get("/accurate-intake/debug/surface", response_class=HTMLResponse)
async def accurate_intake_debug_surface(
    user_id: str = "default_user",
    local_date: str | None = None,
    db: Any = Depends(get_db),
    _local_debug_access: None = Depends(require_local_debug_access),
) -> HTMLResponse:
    payload = build_accurate_intake_debug_payload(db, user_external_id=user_id, local_date=local_date)
    return HTMLResponse(
        content=render_accurate_intake_debug_surface(payload),
        media_type="text/html; charset=utf-8",
    )


@router.post("/accurate-intake/feedback")
async def accurate_intake_feedback(
    payload: dict[str, Any] = Body(...),
    db: Any = Depends(get_db),
    _local_debug_access: None = Depends(require_local_debug_access),
) -> dict[str, Any]:
    started_at = perf_counter()
    try:
        auto_context = build_feedback_auto_context_from_backend(
            db=db,
            payload=payload,
            chat_history_builder=build_accurate_intake_chat_history_payload,
            debug_payload_builder=build_accurate_intake_debug_payload,
        )
        record = build_feedback_record_from_route_payload(
            payload,
            submitted_endpoint="/accurate-intake/feedback",
            duration_ms=round((perf_counter() - started_at) * 1000),
            auto_context=auto_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return append_desktop_feedback_record(record=record, feedback_dir=DOGFOOD_FEEDBACK_DIR)


@router.get("/accurate-intake/review-queue")
async def accurate_intake_review_queue(
    _local_debug_access: None = Depends(require_local_debug_access),
) -> dict[str, Any]:
    return build_desktop_review_queue_response(
        feedback_dir=DOGFOOD_FEEDBACK_DIR,
        review_queue_artifact_path=DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH,
    )
