from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.body.application.active_body_plan_read_model import build_active_body_plan_view
from app.budget.interface.today_surface import resolve_today_local_date
from app.composition.accurate_intake_debug_read_model import build_accurate_intake_debug_read_model
from app.composition.current_budget_read_model import build_current_budget_view
from app.database import get_db
from app.intake.interface.accurate_intake_debug_surface import render_accurate_intake_debug_surface
from app.shared.infra.models import MessageBuffer, User

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


def _runtime_turn_trace(message: MessageBuffer) -> dict[str, Any]:
    trace_json = message.trace_json if isinstance(message.trace_json, dict) else {}
    runtime_turn_trace = trace_json.get("runtime_turn_trace")
    return dict(runtime_turn_trace) if isinstance(runtime_turn_trace, dict) else {}


def _message_local_date(message: MessageBuffer) -> str | None:
    trace = _runtime_turn_trace(message)
    value = trace.get("local_date")
    return str(value) if value else None


def _trace_chain_complete(trace: dict[str, Any]) -> bool:
    chain = trace.get("trace_chain")
    if not isinstance(chain, dict):
        return False
    required = (
        "manager_decision_present",
        "evidence_packet_present",
        "evidence_requirement_satisfied",
        "final_mapping_present",
        "state_before_present",
        "state_after_present",
    )
    chat_linkage = trace.get("chat_linkage") if isinstance(trace.get("chat_linkage"), dict) else {}
    return (
        all(chain.get(key) is True for key in required)
        and chat_linkage.get("user_message_id") is not None
        and chat_linkage.get("assistant_message_id") is not None
    )


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _manager_context_summary(trace: dict[str, Any]) -> dict[str, Any]:
    packet = _dict_or_empty(trace.get("manager_context_packet_v1"))
    hard_pins = _dict_or_empty(packet.get("hard_pins"))
    target_candidates = _dict_or_empty(packet.get("target_candidates"))
    correction_targets = target_candidates.get("for_correction_or_removal")
    if not isinstance(correction_targets, list):
        correction_targets = []
    pending_pin_keys = ("pending_followup", "pending_draft")
    return {
        "context_policy_version": trace.get("context_policy_version"),
        "loaded_context_summary": _dict_or_empty(trace.get("loaded_context_summary")),
        "omitted_context_summary": _dict_or_empty(trace.get("omitted_context_summary")),
        "pending_pins_present": any(bool(_dict_or_empty(hard_pins.get(key))) for key in pending_pin_keys),
        "target_candidates_present": bool(correction_targets),
        "target_candidate_count": len(correction_targets),
    }


def _chat_history_message(message: MessageBuffer) -> dict[str, Any]:
    trace = _runtime_turn_trace(message)
    assistant_response = trace.get("assistant_response") if isinstance(trace.get("assistant_response"), dict) else {}
    context_snapshot = trace.get("context_snapshot") if isinstance(trace.get("context_snapshot"), dict) else {}
    manager_context = _manager_context_summary(trace)
    return {
        "message_id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "trace_id": message.trace_id,
        "linked_meal_log_id": message.linked_meal_log_id,
        "local_date": _message_local_date(message),
        "source": "sqlite_message_buffer",
        "read_only": True,
        "mutation_authority": False,
        "runtime_turn_trace_present": bool(trace),
        "context_snapshot_present": bool(context_snapshot),
        "trace_chain_complete": _trace_chain_complete(trace),
        "pending_followup_linkage_present": isinstance(trace.get("pending_followup_linkage"), dict),
        "structured_followup_question": assistant_response.get("structured_followup_question"),
        **manager_context,
    }


def build_accurate_intake_chat_history_payload(
    db: Any,
    *,
    user_external_id: str,
    local_date: str | None,
) -> dict[str, Any]:
    resolved_local_date = resolve_today_local_date(local_date)
    user = db.query(User).filter(User.user_id == user_external_id).first()
    messages: list[dict[str, Any]] = []
    if user is not None:
        rows = (
            db.query(MessageBuffer)
            .filter(MessageBuffer.user_id == user.id)
            .order_by(MessageBuffer.created_at.asc(), MessageBuffer.id.asc())
            .all()
        )
        messages = [
            _chat_history_message(message)
            for message in rows
            if _message_local_date(message) == resolved_local_date
        ]
    return {
        "surface_id": "accurate_intake_chat_history_v1",
        "read_only": True,
        "source": "sqlite_message_buffer",
        "frontend_semantic_owner": False,
        "scope": "current_session_current_day",
        "long_term_memory_used": False,
        "proactive_or_rescue_used": False,
        "user_external_id": user_external_id,
        "user_id": user.id if user is not None else None,
        "local_date": resolved_local_date,
        "message_count": len(messages),
        "messages": messages,
    }


@router.get("/accurate-intake/debug")
async def accurate_intake_debug(
    user_id: str = "default_user",
    local_date: str | None = None,
    db: Any = Depends(get_db),
) -> dict[str, Any]:
    return build_accurate_intake_debug_payload(db, user_external_id=user_id, local_date=local_date)


@router.get("/accurate-intake/chat-history")
async def accurate_intake_chat_history(
    user_id: str = "default_user",
    local_date: str | None = None,
    db: Any = Depends(get_db),
) -> dict[str, Any]:
    return build_accurate_intake_chat_history_payload(db, user_external_id=user_id, local_date=local_date)


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
