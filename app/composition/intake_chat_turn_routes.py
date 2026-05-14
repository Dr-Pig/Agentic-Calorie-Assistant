from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.composition.inflight_chat_turn import PENDING_ASSISTANT_MESSAGE, record_inflight_intake_chat_turn
from app.composition.manager_context_runtime import build_runtime_manager_context_packet_v1
from app.composition.state_resolver import resolve_intake_state
from app.database import SessionLocal, get_db
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.intake.application.workflow_routing import build_workflow_routing_decision
from app.schemas import EstimateRequest

router = APIRouter()


def _request_local_date(request: EstimateRequest) -> str:
    return request.local_date or datetime.now().date().isoformat()


async def _complete_chat_turn_background(
    request_payload: dict[str, Any],
    *,
    source_page_version: str | None,
) -> None:
    from app.composition import intake_routes

    db = SessionLocal()
    try:
        request = EstimateRequest.model_validate(request_payload)
        raw_request = SimpleNamespace(headers={"X-Canary-Page-Version": source_page_version} if source_page_version else {})
        await intake_routes.estimate(request, raw_request, db)
    finally:
        db.close()


@router.post("/accurate-intake/chat-turn", status_code=202)
async def accurate_intake_chat_turn(
    request: EstimateRequest,
    raw_request: Request,
    background_tasks: BackgroundTasks,
    db: Any = Depends(get_db),
) -> dict[str, Any]:
    request_id = request.request_id or uuid4().hex
    user_id = request.user_id if getattr(request, "user_id", None) else "default_user"
    local_date = _request_local_date(request)
    state_before = resolve_intake_state(
        db,
        user_external_id=user_id,
        local_date=local_date,
        incoming_user_text=request.text,
        exclude_trace_id=request_id,
    )
    current_turn_context = build_current_turn_context_v1(
        raw_user_input=request.text,
        resolved_state=state_before,
    )
    manager_context_packet_v1 = build_runtime_manager_context_packet_v1(
        db=db,
        current_turn_context=current_turn_context,
        user_external_id=user_id,
        local_date=local_date,
        session_id=request_id,
        exclude_trace_id=request_id,
    )
    routing_result = build_workflow_routing_decision(
        raw_user_input=request.text,
        current_turn_context=current_turn_context,
        resolved_state=state_before,
    )
    record_inflight_intake_chat_turn(
        db,
        user_external_id=user_id,
        request_id=request_id,
        local_date=local_date,
        raw_user_input=request.text,
        state_before=state_before,
        current_turn_context=current_turn_context,
        manager_context_packet_v1=manager_context_packet_v1,
        phase_a_trace=routing_result.phase_a_trace,
    )
    request_payload = request.model_dump(mode="json")
    request_payload["request_id"] = request_id
    background_tasks.add_task(
        _complete_chat_turn_background,
        request_payload,
        source_page_version=raw_request.headers.get("X-Canary-Page-Version"),
    )
    return {
        "status": "accepted",
        "request_id": request_id,
        "trace_id": request_id,
        "coach_message": PENDING_ASSISTANT_MESSAGE,
        "local_date": local_date,
    }


__all__ = ["router"]
