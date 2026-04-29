from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from ...body.application.active_body_plan_read_model import build_active_body_plan_view
from ...budget.application.current_budget_read_model import build_current_budget_view
from ...database import get_or_create_user
from ..infrastructure.conversation_state_loader import load_conversation_state
from ...text_integrity import sanitize_text_structure, sanitize_text_value


@dataclass(frozen=True)
class V2ResolvedState:
    user_external_id: str
    user_id: int
    local_date: str
    onboarding_ready: bool
    active_body_plan_view: Any
    current_budget_view: Any
    active_meal: dict[str, Any] | None
    conversation_state: Any
    injected_context: dict[str, Any]


def _active_meal_summary(current_budget_view: Any) -> dict[str, Any] | None:
    if not current_budget_view.meals:
        return None
    latest_meal = max(
        current_budget_view.meals,
        key=lambda meal: meal.occurred_at.isoformat() if meal.occurred_at is not None else "",
    )
    return {
        "meal_thread_id": latest_meal.meal_thread_id,
        "meal_version_id": latest_meal.meal_version_id,
        "meal_title": sanitize_text_value(latest_meal.meal_title),
        "total_kcal": latest_meal.total_kcal,
        "occurred_at": latest_meal.occurred_at.isoformat() if latest_meal.occurred_at is not None else None,
        "resolution_status": latest_meal.resolution_status,
    }


def _recent_committed_meal_summaries(current_budget_view: Any, *, limit: int = 3) -> list[dict[str, Any]]:
    meals = list(current_budget_view.meals or [])
    if not meals:
        return []
    recent = sorted(
        meals,
        key=lambda meal: meal.occurred_at.isoformat() if meal.occurred_at is not None else "",
        reverse=True,
    )[:limit]
    return [
        {
            "meal_thread_id": meal.meal_thread_id,
            "meal_version_id": meal.meal_version_id,
            "meal_title": sanitize_text_value(meal.meal_title),
            "total_kcal": meal.total_kcal,
            "occurred_at": meal.occurred_at.isoformat() if meal.occurred_at is not None else None,
            "source_request_id": meal.source_request_id,
        }
        for meal in recent
    ]


def _target_meal_reference(*, active_meal: dict[str, Any] | None, conversation_state: Any) -> dict[str, Any]:
    pending_state = getattr(conversation_state, "pending_followup_state", None)
    active_state = getattr(conversation_state, "active_meal_state", None)
    meal_thread_id = active_meal.get("meal_thread_id") if isinstance(active_meal, dict) else None
    meal_version_id = active_meal.get("meal_version_id") if isinstance(active_meal, dict) else None
    meal_title = active_meal.get("meal_title") if isinstance(active_meal, dict) else None
    source = "active_meal_view" if meal_thread_id is not None else "none"
    confidence = "medium" if meal_thread_id is not None else "low"
    if getattr(pending_state, "is_open", False):
        source = "pending_followup_state"
        confidence = "high"
    if getattr(active_state, "meal_title", None) and meal_title is None:
        meal_title = sanitize_text_value(active_state.meal_title)
    return {
        "meal_thread_id": meal_thread_id,
        "meal_version_id": meal_version_id,
        "meal_title": sanitize_text_value(meal_title),
        "target_resolution_source": source,
        "correction_confidence": confidence,
    }


def _overshoot_posture(current_budget_view: Any) -> dict[str, Any]:
    return {
        "budget_kcal": int(current_budget_view.budget_kcal or 0),
        "consumed_kcal_before": int(current_budget_view.consumed_kcal or 0),
        "predicted_consumed_kcal_after": int(current_budget_view.consumed_kcal or 0),
        "predicted_remaining_kcal_after": int(current_budget_view.remaining_kcal or 0),
        "overshoot_detected": int(current_budget_view.remaining_kcal or 0) < 0,
        "overshoot_kcal": abs(min(int(current_budget_view.remaining_kcal or 0), 0)),
    }


def _injected_context(
    *,
    active_body_plan_view: Any,
    current_budget_view: Any,
    active_meal: dict[str, Any] | None,
    conversation_state: Any,
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
    return {
        "CURRENT_BUDGET": {
            "budget_kcal": int(current_budget_view.budget_kcal or 0),
            "consumed_kcal": int(current_budget_view.consumed_kcal or 0),
            "remaining_kcal": int(current_budget_view.remaining_kcal or 0),
            "active_meal_count": int(current_budget_view.active_meal_count or 0),
        },
        "ACTIVE_BODY_PLAN": {
            "body_plan_id": active_body_plan_view.body_plan_id,
            "goal_type": active_body_plan_view.goal_type,
            "daily_budget_kcal": int(active_body_plan_view.daily_budget_kcal or 0),
            "estimated_tdee": int(active_body_plan_view.estimated_tdee or 0),
            "safety_floor_kcal": int(active_body_plan_view.safety_floor_kcal or 0),
        },
        "ACTIVE_MEAL": active_meal,
        "PENDING_FOLLOWUP": sanitize_text_structure(pending_payload),
        "RECENT_COMMITTED_MEALS_SUMMARY": _recent_committed_meal_summaries(current_budget_view),
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


def resolve_v2_bundle1_state(
    db: Session,
    *,
    user_external_id: str,
    local_date: str,
    incoming_user_text: str | None = None,
) -> V2ResolvedState:
    user = get_or_create_user(db, user_external_id)
    active_body_plan_view = build_active_body_plan_view(db, user_id=user.id)
    current_budget_view = build_current_budget_view(db, user_id=user.id, local_date=local_date)
    active_meal = _active_meal_summary(current_budget_view)
    loaded_context = load_conversation_state(
        db,
        user_id=user_external_id,
        incoming_user_text=incoming_user_text,
        persist_incoming_user_text=False,
    )
    conversation_state = loaded_context.state
    injected_context = _injected_context(
        active_body_plan_view=active_body_plan_view,
        current_budget_view=current_budget_view,
        active_meal=active_meal,
        conversation_state=conversation_state,
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
