from __future__ import annotations

import asyncio
import json
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.composition.inflight_chat_turn import (
    PENDING_ASSISTANT_MESSAGE,
    QUEUED_ASSISTANT_MESSAGE,
    record_inflight_intake_chat_turn,
    record_queued_intake_chat_turn,
)
from app.composition.conversation_turn_trace import record_runtime_turn_messages
from app.composition.manager_context_runtime import build_runtime_manager_context_packet_v1
from app.composition.state_resolver import resolve_intake_state
from app.database import SessionLocal, get_db
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.intake.application.workflow_routing import build_workflow_routing_decision
from app.schemas import EstimateRequest
from app.shared.infra.models import MessageBuffer, User

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
        response = await intake_routes.estimate(request, raw_request, db)
        error_payload = _estimate_error_payload(response)
        if error_payload is not None:
            _record_failed_chat_turn_completion(
                db,
                request=request,
                error_payload=error_payload,
            )
    finally:
        db.close()


def _estimate_error_payload(response: Any) -> dict[str, Any] | None:
    if isinstance(response, dict):
        return response if response.get("error") else None
    status_code = int(getattr(response, "status_code", 200) or 200)
    if status_code < 400:
        return None
    body = getattr(response, "body", b"")
    try:
        payload = json.loads(body.decode("utf-8") if isinstance(body, bytes) else str(body))
    except Exception:
        payload = {"error": f"http_{status_code}", "coach_message": "抱歉，這次沒有處理成功，請再送一次。"}
    return payload if isinstance(payload, dict) else {"error": f"http_{status_code}"}


def _record_failed_chat_turn_completion(
    db: Any,
    *,
    request: EstimateRequest,
    error_payload: dict[str, Any],
) -> None:
    user_id = request.user_id if getattr(request, "user_id", None) else "default_user"
    local_date = _request_local_date(request)
    request_id = str(request.request_id or error_payload.get("request_id") or uuid4().hex)
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
    assistant_message = str(
        error_payload.get("coach_message") or "抱歉，這次沒有處理成功，請再送一次。"
    )
    record_runtime_turn_messages(
        db,
        user_external_id=user_id,
        request_id=request_id,
        local_date=local_date,
        raw_user_input=request.text,
        assistant_message=assistant_message,
        state_before=state_before,
        current_turn_context=current_turn_context,
        manager_context_packet_v1=manager_context_packet_v1,
        state_after=state_before,
        phase_a_trace={"runtime_turn_status": "failed"},
        result={
            "manager_decision": {
                "intent_type": "runtime_error",
                "workflow_effect": "runtime_error",
                "tool_calls": [],
            },
            "intake_execution_manager": {
                "final": {"final_action": "answer_only", "workflow_effect": "runtime_error"},
                "persistence_result": None,
            },
            "state_delta": {},
            "sidecar": {
                "runtime_turn_status": "failed",
                "error": str(error_payload.get("error") or "runtime_error"),
            },
        },
    )


def _runtime_turn_status_from_message(message: MessageBuffer) -> str:
    trace_json = message.trace_json if isinstance(message.trace_json, dict) else {}
    runtime_turn_trace = trace_json.get("runtime_turn_trace")
    trace = runtime_turn_trace if isinstance(runtime_turn_trace, dict) else {}
    context_snapshot = trace.get("context_snapshot") if isinstance(trace.get("context_snapshot"), dict) else {}
    phase_a_trace = context_snapshot.get("phase_a_trace") if isinstance(context_snapshot.get("phase_a_trace"), dict) else {}
    if phase_a_trace.get("runtime_turn_status") in {"in_progress", "queued"}:
        return str(phase_a_trace.get("runtime_turn_status"))
    final_mapping = trace.get("final_mapping") if isinstance(trace.get("final_mapping"), dict) else {}
    if final_mapping.get("final_action") == "queued":
        return "queued"
    if final_mapping.get("final_action") == "pending":
        return "in_progress"
    return "completed" if trace else "not_available"


def _message_local_date(message: MessageBuffer) -> str | None:
    trace_json = message.trace_json if isinstance(message.trace_json, dict) else {}
    runtime_turn_trace = trace_json.get("runtime_turn_trace")
    trace = runtime_turn_trace if isinstance(runtime_turn_trace, dict) else {}
    value = trace.get("local_date")
    return str(value) if value else None


def _latest_open_turn_request_id(
    db: Any,
    *,
    user_external_id: str,
    local_date: str,
    exclude_request_id: str,
) -> str | None:
    user = db.query(User).filter(User.user_id == user_external_id).first()
    if user is None:
        return None
    rows = (
        db.query(MessageBuffer)
        .filter(MessageBuffer.user_id == user.id, MessageBuffer.role == "assistant")
        .order_by(MessageBuffer.created_at.desc(), MessageBuffer.id.desc())
        .all()
    )
    for row in rows:
        if row.trace_id == exclude_request_id or _message_local_date(row) != local_date:
            continue
        if _runtime_turn_status_from_message(row) in {"in_progress", "queued"}:
            return str(row.trace_id or "")
    return None


def _turn_is_open(db: Any, *, request_id: str) -> bool:
    if not request_id:
        return False
    rows = db.query(MessageBuffer).filter(MessageBuffer.trace_id == request_id).all()
    return any(_runtime_turn_status_from_message(row) in {"in_progress", "queued"} for row in rows)


async def _complete_queued_chat_turn_background(
    request_payload: dict[str, Any],
    *,
    source_page_version: str | None,
    wait_for_request_id: str,
) -> None:
    deadline = asyncio.get_running_loop().time() + 180
    while True:
        db = SessionLocal()
        try:
            still_open = _turn_is_open(db, request_id=wait_for_request_id)
        finally:
            db.close()
        if not still_open:
            break
        if asyncio.get_running_loop().time() > deadline:
            break
        await asyncio.sleep(1)
    await _complete_chat_turn_background(
        request_payload,
        source_page_version=source_page_version,
    )


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
    queued_after_request_id = _latest_open_turn_request_id(
        db,
        user_external_id=user_id,
        local_date=local_date,
        exclude_request_id=request_id,
    )
    request_payload = request.model_dump(mode="json")
    request_payload["request_id"] = request_id
    source_page_version = raw_request.headers.get("X-Canary-Page-Version")
    if queued_after_request_id:
        record_queued_intake_chat_turn(
            db,
            user_external_id=user_id,
            request_id=request_id,
            queued_after_request_id=queued_after_request_id,
            local_date=local_date,
            raw_user_input=request.text,
            state_before=state_before,
            current_turn_context=current_turn_context,
            manager_context_packet_v1=manager_context_packet_v1,
            phase_a_trace=routing_result.phase_a_trace,
        )
        background_tasks.add_task(
            _complete_queued_chat_turn_background,
            request_payload,
            source_page_version=source_page_version,
            wait_for_request_id=queued_after_request_id,
        )
        return {
            "status": "queued",
            "request_id": request_id,
            "trace_id": request_id,
            "queued_after_request_id": queued_after_request_id,
            "coach_message": QUEUED_ASSISTANT_MESSAGE,
            "local_date": local_date,
        }
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
    background_tasks.add_task(
        _complete_chat_turn_background,
        request_payload,
        source_page_version=source_page_version,
    )
    return {
        "status": "accepted",
        "request_id": request_id,
        "trace_id": request_id,
        "coach_message": PENDING_ASSISTANT_MESSAGE,
        "local_date": local_date,
    }


__all__ = ["router"]
