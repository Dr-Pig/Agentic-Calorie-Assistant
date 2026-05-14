from __future__ import annotations

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.composition.manager_context_meal_basis import (
    active_meal_basis_target_candidates,
    build_active_meal_estimate_basis,
)
from app.intake.application.manager_context_policy import build_manager_context_packet_v1
from app.intake.infrastructure.models import MealThreadRecord, MealVersionRecord
from app.runtime.contracts.phase_a import CurrentTurnContextV1
from app.shared.infra.models import MessageBuffer, User

MANAGER_CONTEXT_RECENT_MESSAGE_LIMIT = 20
MANAGER_CONTEXT_RECENT_SCAN_LIMIT = 500


def _message_local_date(message: MessageBuffer) -> str | None:
    trace = dict(message.trace_json or {})
    runtime_turn = dict(trace.get("runtime_turn_trace") or {})
    trace_meta = dict(trace.get("trace_meta") or {})
    return (
        str(runtime_turn.get("local_date") or "").strip()
        or str(trace_meta.get("local_date") or "").strip()
        or None
    )


def _structured_followup_question(message: MessageBuffer) -> str | None:
    trace = dict(message.trace_json or {})
    runtime_turn = dict(trace.get("runtime_turn_trace") or {})
    assistant_response = dict(runtime_turn.get("assistant_response") or {})
    question = str(assistant_response.get("structured_followup_question") or "").strip()
    if question:
        return question
    trace_contract = dict(trace.get("trace_contract") or {})
    question = str(trace_contract.get("followup_question") or "").strip()
    return question or None


def _packet_recent_chat_turns(
    db: Session | None,
    *,
    user_external_id: str,
    local_date: str,
    limit: int = MANAGER_CONTEXT_RECENT_MESSAGE_LIMIT,
    scan_limit: int = MANAGER_CONTEXT_RECENT_SCAN_LIMIT,
) -> list[dict[str, Any]]:
    if db is None:
        return []
    user = db.query(User).filter(User.user_id == user_external_id).first()
    if user is None:
        return []
    bounded_scan_limit = max(int(scan_limit or 0), int(limit or 0), 0)
    if bounded_scan_limit == 0:
        return []
    rows = (
        db.query(MessageBuffer)
        .filter(MessageBuffer.user_id == user.id)
        .order_by(desc(MessageBuffer.created_at), desc(MessageBuffer.id))
        .limit(bounded_scan_limit)
        .all()
    )
    same_day = [message for message in rows if _message_local_date(message) == local_date]
    selected = list(reversed(same_day))
    turns: list[dict[str, Any]] = []
    for message in selected:
        turn = {
            "message_id": message.id,
            "role": str(message.role or ""),
            "content": str(message.content or ""),
            "created_at": message.created_at.isoformat() if message.created_at is not None else None,
            "trace_id": message.trace_id,
            "linked_meal_log_id": message.linked_meal_log_id,
            "local_date": _message_local_date(message),
            "read_only": True,
            "mutation_authority": False,
            "source": "sqlite_message_buffer",
        }
        followup_question = _structured_followup_question(message)
        if followup_question:
            turn["structured_followup_question"] = followup_question
        turns.append(turn)
    return turns


def _pending_draft_snapshot(
    db: Session | None,
    *,
    user_external_id: str,
    local_date: str,
) -> dict[str, Any] | None:
    if db is None:
        return None
    user = db.query(User).filter(User.user_id == user_external_id).first()
    if user is None:
        return None
    row = (
        db.execute(
            select(MealThreadRecord, MealVersionRecord)
            .join(MealVersionRecord, MealThreadRecord.id == MealVersionRecord.meal_thread_id)
            .where(
                MealThreadRecord.user_id == user.id,
                MealVersionRecord.local_date == local_date,
                MealVersionRecord.version_status != "superseded",
                MealVersionRecord.resolution_status.in_(("candidate_meal", "draft_unresolved")),
            )
            .order_by(desc(MealVersionRecord.created_at), desc(MealVersionRecord.id))
            .limit(1)
        )
        .first()
    )
    if row is None:
        return None
    thread, version = row
    return {
        "meal_thread_id": thread.id,
        "meal_version_id": version.id,
        "meal_title": str(version.meal_title or thread.title or ""),
        "resolution_status": str(version.resolution_status or ""),
        "source_request_id": version.source_request_id,
    }


def build_runtime_manager_context_packet_v1(
    *,
    db: Session | None = None,
    current_turn_context: CurrentTurnContextV1 | None,
    user_external_id: str,
    local_date: str,
    session_id: str | None = None,
    channel: str = "web_shell",
    manager_mode: str = "fixture",
) -> dict[str, Any] | None:
    if not isinstance(current_turn_context, CurrentTurnContextV1):
        return None
    packet_turns = _packet_recent_chat_turns(
        db,
        user_external_id=user_external_id,
        local_date=local_date,
        limit=MANAGER_CONTEXT_RECENT_MESSAGE_LIMIT,
    )
    pending_draft = _pending_draft_snapshot(
        db,
        user_external_id=user_external_id,
        local_date=local_date,
    )
    active_meal_basis = build_active_meal_estimate_basis(
        db,
        user_external_id=user_external_id,
        local_date=local_date,
    )
    target_candidates = [
        *active_meal_basis_target_candidates(active_meal_basis),
        *list(current_turn_context.candidate_attachment_targets or []),
        *list(current_turn_context.recent_item_targets or []),
    ]
    packet_context = (
        current_turn_context.model_copy(update={"recent_chat_turns": packet_turns})
        if packet_turns
        else current_turn_context
    )
    return build_manager_context_packet_v1(
        current_turn_context=packet_context,
        user_id=user_external_id,
        local_date=local_date,
        session_id=session_id or f"{user_external_id}:{local_date}",
        channel=channel,
        manager_mode=manager_mode,
        pending_draft=pending_draft,
        active_day_state={"active_meal_estimate_basis": active_meal_basis} if active_meal_basis else None,
        target_candidates=target_candidates,
    )


__all__ = [
    "MANAGER_CONTEXT_RECENT_MESSAGE_LIMIT",
    "MANAGER_CONTEXT_RECENT_SCAN_LIMIT",
    "build_runtime_manager_context_packet_v1",
]
