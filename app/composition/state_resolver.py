from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.body.application.active_body_plan_read_model import build_active_body_plan_view
from app.budget.infrastructure.models import DayBudgetLedgerRecord
from app.composition.current_budget_read_model import build_current_budget_view
from app.database import get_or_create_user
from app.intake.infrastructure.models import MealItemRecord
from app.shared.infra.models import MessageBuffer
from app.composition.state_contracts import V2ResolvedState
from .conversation_state_loader import load_conversation_state
from app.text_integrity import sanitize_text_structure, sanitize_text_value


def _item_target_reference_for_version(db: Session, *, meal_version_id: int | None) -> dict[str, Any]:
    if meal_version_id is None:
        return {"item_resolution_source": "none"}
    items = db.execute(
        select(MealItemRecord)
        .where(MealItemRecord.meal_version_id == meal_version_id)
        .order_by(MealItemRecord.item_index.asc())
    ).scalars().all()
    if not items:
        return {"item_resolution_source": "none"}
    item_candidates = [
        {
            "meal_item_id": item.id,
            "canonical_name": sanitize_text_value(item.name),
            "item_index": item.item_index,
            "estimated_kcal": int(item.estimated_kcal or 0),
            "mutation_authority": False,
            "selected_target": False,
        }
        for item in items
    ]
    if len(items) != 1:
        return {
            "item_resolution_source": "ambiguous_active_items",
            "item_candidates": item_candidates,
        }
    item = items[0]
    return {
        "meal_item_id": item.id,
        "canonical_name": sanitize_text_value(item.name),
        "item_resolution_source": "single_active_item",
    }


def _active_meal_summary(db: Session, current_budget_view: Any) -> dict[str, Any] | None:
    if not current_budget_view.meals:
        return None
    latest_meal = max(
        current_budget_view.meals,
        key=lambda meal: meal.occurred_at.isoformat() if meal.occurred_at is not None else "",
    )
    summary = {
        "meal_thread_id": latest_meal.meal_thread_id,
        "meal_version_id": latest_meal.meal_version_id,
        "meal_title": sanitize_text_value(latest_meal.meal_title),
        "total_kcal": latest_meal.total_kcal,
        "occurred_at": latest_meal.occurred_at.isoformat() if latest_meal.occurred_at is not None else None,
        "resolution_status": latest_meal.resolution_status, "read_only": True, "mutation_authority": False,
    }
    summary.update(_item_target_reference_for_version(db, meal_version_id=latest_meal.meal_version_id))
    return summary


def _recent_committed_meal_summaries(
    db: Session,
    current_budget_view: Any,
    *,
    limit: int = 4,
) -> list[dict[str, Any]]:
    meals = list(current_budget_view.meals or [])
    if not meals:
        return []
    recent = sorted(
        meals,
        key=lambda meal: meal.occurred_at.isoformat() if meal.occurred_at is not None else "",
        reverse=True,
    )[:limit]
    summaries: list[dict[str, Any]] = []
    for meal in recent:
        summary = {
            "meal_thread_id": meal.meal_thread_id,
            "meal_version_id": meal.meal_version_id,
            "meal_title": sanitize_text_value(meal.meal_title),
            "total_kcal": meal.total_kcal,
            "occurred_at": meal.occurred_at.isoformat() if meal.occurred_at is not None else None,
            "source_request_id": meal.source_request_id, "read_only": True, "mutation_authority": False,
        }
        summary.update(_item_target_reference_for_version(db, meal_version_id=meal.meal_version_id))
        summaries.append(summary)
    return summaries


def _target_meal_reference(*, active_meal: dict[str, Any] | None, conversation_state: Any) -> dict[str, Any]:
    pending_state = getattr(conversation_state, "pending_followup_state", None)
    active_state = getattr(conversation_state, "active_meal_state", None)
    meal_thread_id = active_meal.get("meal_thread_id") if isinstance(active_meal, dict) else None
    meal_version_id = active_meal.get("meal_version_id") if isinstance(active_meal, dict) else None
    meal_title = active_meal.get("meal_title") if isinstance(active_meal, dict) else None
    meal_item_id = active_meal.get("meal_item_id") if isinstance(active_meal, dict) else None
    canonical_name = active_meal.get("canonical_name") if isinstance(active_meal, dict) else None
    item_resolution_source = active_meal.get("item_resolution_source") if isinstance(active_meal, dict) else None
    item_candidates = active_meal.get("item_candidates") if isinstance(active_meal, dict) else None
    source = "active_meal_view" if meal_thread_id is not None else "none"
    confidence = "medium" if meal_thread_id is not None else "low"
    if getattr(pending_state, "is_open", False):
        source = "pending_followup_state"
        confidence = "high"
    if getattr(active_state, "meal_title", None) and meal_title is None:
        meal_title = sanitize_text_value(active_state.meal_title)
    reference = {
        "meal_thread_id": meal_thread_id,
        "meal_version_id": meal_version_id,
        "meal_title": sanitize_text_value(meal_title),
        "target_resolution_source": source,
        "correction_confidence": confidence,
    }
    if meal_item_id is not None:
        reference["meal_item_id"] = meal_item_id
    if canonical_name is not None:
        reference["canonical_name"] = sanitize_text_value(canonical_name)
    if item_resolution_source is not None:
        reference["item_resolution_source"] = item_resolution_source
    if isinstance(item_candidates, list):
        reference["item_candidates"] = sanitize_text_structure(item_candidates)
    return reference


def _overshoot_posture(current_budget_view: Any) -> dict[str, Any]:
    return {
        "budget_kcal": int(current_budget_view.budget_kcal or 0),
        "consumed_kcal_before": int(current_budget_view.consumed_kcal or 0),
        "predicted_consumed_kcal_after": int(current_budget_view.consumed_kcal or 0),
        "predicted_remaining_kcal_after": int(current_budget_view.remaining_kcal or 0),
        "overshoot_detected": int(current_budget_view.remaining_kcal or 0) < 0,
        "overshoot_kcal": abs(min(int(current_budget_view.remaining_kcal or 0), 0)),
    }


def _day_budget_ledger_posture(db: Session, *, user_id: int, local_date: str) -> tuple[bool, str | None]:
    ledger = db.execute(
        select(DayBudgetLedgerRecord).where(
            DayBudgetLedgerRecord.user_id == user_id,
            DayBudgetLedgerRecord.local_date == local_date,
        )
    ).scalar_one_or_none()
    if ledger is None:
        return False, None
    return True, ledger.last_recomputed_at.isoformat() if ledger.last_recomputed_at is not None else None


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
        return sanitize_text_value(question)
    trace_contract = dict(trace.get("trace_contract") or {})
    question = str(trace_contract.get("followup_question") or "").strip()
    return sanitize_text_value(question) if question else None


def _recent_chat_turns(messages: list[MessageBuffer], *, local_date: str, limit: int = 6) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    eligible_messages = [message for message in list(messages or []) if _message_local_date(message) == local_date]
    for message in eligible_messages[-limit:]:
        message_local_date = _message_local_date(message)
        turn = {
            "message_id": message.id,
            "role": sanitize_text_value(message.role),
            "content": sanitize_text_value(message.content),
            "created_at": message.created_at.isoformat() if message.created_at is not None else None,
            "trace_id": message.trace_id,
            "linked_meal_log_id": message.linked_meal_log_id,
            "local_date": message_local_date,
            "read_only": True,
            "mutation_authority": False,
            "source": "sqlite_message_buffer",
        }
        followup_question = _structured_followup_question(message)
        if followup_question:
            turn["structured_followup_question"] = followup_question
        turns.append(turn)
    return turns


def _injected_context(
    *,
    db: Session,
    active_body_plan_view: Any,
    current_budget_view: Any,
    active_meal: dict[str, Any] | None,
    conversation_state: Any,
    recent_messages: list[MessageBuffer],
) -> dict[str, Any]:
    pending_followup = getattr(conversation_state, "pending_followup_state", None)
    session_summary = getattr(conversation_state, "session_summary", None)
    pending_payload = (
        pending_followup.model_dump(mode="json")
        if pending_followup is not None
        else {
            "is_open": False,
            "source_meal_id": None,
            "pending_question": None,
            "missing_high_impact_slots": [],
        }
    )
    session_payload = session_summary.model_dump(mode="json") if session_summary is not None else {}
    has_active_plan = active_body_plan_view.body_plan_id is not None
    has_day_budget_ledger, ledger_last_recomputed_at = _day_budget_ledger_posture(
        db,
        user_id=current_budget_view.user_id,
        local_date=current_budget_view.local_date,
    )
    return {
        "CURRENT_BUDGET": {
            "local_date": current_budget_view.local_date,
            "budget_kcal": int(current_budget_view.budget_kcal or 0),
            "consumed_kcal": int(current_budget_view.consumed_kcal or 0),
            "remaining_kcal": int(current_budget_view.remaining_kcal or 0),
            "active_meal_count": int(current_budget_view.active_meal_count or 0),
            "has_active_plan": has_active_plan,
            "has_day_budget_ledger": has_day_budget_ledger,
            "ledger_last_recomputed_at": ledger_last_recomputed_at,
            "no_plan_posture": "not_applicable" if has_active_plan else "onboarding_required",
            "overshoot_status": "overshoot" if int(current_budget_view.remaining_kcal or 0) < 0 else "within_budget",
            "freshness_status": "current_turn",
        },
        "ACTIVE_BODY_PLAN": {
            "body_plan_id": active_body_plan_view.body_plan_id,
            "goal_type": active_body_plan_view.goal_type,
            "daily_budget_kcal": int(active_body_plan_view.daily_budget_kcal or 0),
            "estimated_tdee": int(active_body_plan_view.estimated_tdee or 0),
            "safety_floor_kcal": int(active_body_plan_view.safety_floor_kcal or 0),
            "freshness_status": "current_turn",
        },
        "ACTIVE_MEAL": active_meal,
        "PENDING_FOLLOWUP": sanitize_text_structure(pending_payload),
        "RECENT_CHAT_TURNS": sanitize_text_structure(
            _recent_chat_turns(recent_messages, local_date=current_budget_view.local_date)
        ),
        "RECENT_COMMITTED_MEALS_SUMMARY": _recent_committed_meal_summaries(db, current_budget_view),
        "TARGET_MEAL_REFERENCE": _target_meal_reference(
            active_meal=active_meal,
            conversation_state=conversation_state,
        ),
        "OVERSHOOT_POSTURE": _overshoot_posture(current_budget_view),
        "NEGATIVE_PREFERENCES": [],
        "MEMORY_FRESHNESS": {
            "posture": "unknown",
            "last_updated": None,
        },
        "SESSION_SUMMARY": sanitize_text_structure(session_payload),
    }


def resolve_intake_state(
    db: Session,
    *,
    user_external_id: str,
    local_date: str,
    incoming_user_text: str | None = None, exclude_trace_id: str | None = None,
) -> V2ResolvedState:
    user = get_or_create_user(db, user_external_id)
    active_body_plan_view = build_active_body_plan_view(db, user_id=user.id)
    current_budget_view = build_current_budget_view(db, user_id=user.id, local_date=local_date)
    active_meal = _active_meal_summary(db, current_budget_view)
    loaded_context = load_conversation_state(
        db,
        user_id=user_external_id,
        incoming_user_text=incoming_user_text,
        persist_incoming_user_text=False, exclude_trace_id=exclude_trace_id,
    )
    conversation_state = loaded_context.state
    injected_context = _injected_context(
        db=db,
        active_body_plan_view=active_body_plan_view,
        current_budget_view=current_budget_view,
        active_meal=active_meal,
        conversation_state=conversation_state,
        recent_messages=loaded_context.recent_messages,
    )

    return V2ResolvedState(
        user_external_id=user_external_id,
        user_id=user.id,
        local_date=local_date,
        onboarding_ready=active_body_plan_view.body_plan_id is not None,
        active_body_plan_view=active_body_plan_view,
        current_budget_view=current_budget_view,
        active_meal=active_meal,
        conversation_state=conversation_state,
        injected_context=injected_context,
    )
