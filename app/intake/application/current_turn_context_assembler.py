from __future__ import annotations

from typing import Any

from ...runtime.contracts.phase_a import (
    ContextSourceView,
    CurrentTurnContextV1,
    InteractionEvent,
)

_AMBIGUOUS_TOKENS = {"ok", "okay", "sure", "fine", "good", "yes", "yep"}


def build_chat_interaction_event(
    *,
    raw_user_input: str,
    occurred_at: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> InteractionEvent:
    return InteractionEvent(
        source="chat",
        surface_mode="chat_freeform",
        event_type="user_message",
        raw_text=raw_user_input,
        action_id=None,
        target_object_type="none",
        target_object_id=None,
        occurred_at=occurred_at,
        payload={},
        metadata=dict(metadata or {}),
    )


def _source_view(*, owner: str, availability: str, summary: dict[str, Any] | None = None) -> ContextSourceView:
    return ContextSourceView(
        owner=owner,
        availability=availability,
        summary=dict(summary or {}),
    )


def _normalized_text(raw_user_input: str) -> str:
    return str(raw_user_input or "").strip().lower()


def _looks_like_ambiguous_ack(raw_user_input: str) -> bool:
    normalized = _normalized_text(raw_user_input)
    return normalized in _AMBIGUOUS_TOKENS


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return dict(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return dict(value)
    return {}


def _last_system_question(*, resolved_state: Any, session_summary: dict[str, Any]) -> tuple[str | None, str]:
    assistant_turns = [
        str(item).strip()
        for item in list(session_summary.get("latest_assistant_turns") or [])
        if str(item).strip()
    ]
    if assistant_turns:
        return assistant_turns[-1], "present"
    if getattr(resolved_state, "conversation_state", None) is None:
        return None, "unknown"
    return None, "none"


def _pending_followup_state(pending_followup: dict[str, Any] | None) -> tuple[dict[str, Any] | None, str]:
    if pending_followup is None:
        return None, "unknown"
    if bool(pending_followup.get("is_open")):
        return dict(pending_followup), "present"
    return None, "none"


def _recent_committed_state(recent_meals: Any) -> tuple[list[dict[str, Any]], str]:
    if recent_meals is None:
        return [], "unknown"
    meals = [dict(item) for item in list(recent_meals or []) if isinstance(item, dict)]
    return meals, ("present" if meals else "none")


def _active_meal_thread_state(active_meal: Any) -> tuple[dict[str, Any] | None, str]:
    if not isinstance(active_meal, dict):
        return None, "none"
    if active_meal.get("meal_thread_id") is None:
        return None, "none"
    return dict(active_meal), "present"


def _candidate_attachment_targets(
    *,
    pending_followup: dict[str, Any] | None,
    target_meal_reference: dict[str, Any],
    recent_committed_meals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_target(meal_thread_id: Any, *, source: str, confidence: str) -> None:
        target_id = str(meal_thread_id).strip() if meal_thread_id is not None else ""
        if not target_id or target_id in seen:
            return
        seen.add(target_id)
        targets.append(
            {
                "target_object_type": "meal_thread",
                "target_object_id": target_id,
                "source": source,
                "confidence": confidence,
            }
        )

    if pending_followup is not None:
        add_target(
            pending_followup.get("meal_thread_id"),
            source="pending_followup",
            confidence="high",
        )
    add_target(
        target_meal_reference.get("meal_thread_id"),
        source=str(target_meal_reference.get("target_resolution_source") or "target_meal_reference"),
        confidence=str(target_meal_reference.get("correction_confidence") or "medium"),
    )
    for meal in recent_committed_meals:
        add_target(
            meal.get("meal_thread_id"),
            source="recent_committed_meal",
            confidence="medium",
        )
    return targets


def build_current_turn_context_v1(
    *,
    raw_user_input: str,
    resolved_state: Any,
    interaction_event: InteractionEvent | None = None,
) -> CurrentTurnContextV1:
    injected_context = dict(getattr(resolved_state, "injected_context", {}) or {})
    active_meal = injected_context.get("ACTIVE_MEAL")
    pending_followup_payload = injected_context.get("PENDING_FOLLOWUP")
    recent_meals_payload = injected_context.get("RECENT_COMMITTED_MEALS_SUMMARY")
    target_meal_reference = _as_dict(injected_context.get("TARGET_MEAL_REFERENCE"))
    session_summary = _as_dict(injected_context.get("SESSION_SUMMARY"))

    last_system_question, last_system_question_availability = _last_system_question(
        resolved_state=resolved_state,
        session_summary=session_summary,
    )
    active_meal_thread_ref, active_meal_availability = _active_meal_thread_state(active_meal)
    pending_followup, pending_followup_availability = _pending_followup_state(_as_dict(pending_followup_payload))
    recent_committed_meals, recent_committed_availability = _recent_committed_state(recent_meals_payload)
    current_event = interaction_event or build_chat_interaction_event(raw_user_input=raw_user_input)
    candidate_targets = _candidate_attachment_targets(
        pending_followup=pending_followup,
        target_meal_reference=target_meal_reference,
        recent_committed_meals=recent_committed_meals,
    )

    if pending_followup is not None:
        open_workflow_type = "meal_followup"
    elif target_meal_reference.get("meal_thread_id") is not None:
        open_workflow_type = "meal_correction"
    elif current_event.target_object_type == "proposal":
        open_workflow_type = "proposal"
    elif any(
        availability == "none"
        for availability in (
            active_meal_availability,
            pending_followup_availability,
            recent_committed_availability,
        )
    ):
        open_workflow_type = "none"
    else:
        open_workflow_type = "unknown"

    source_views = {
        "active_meal_thread_ref": _source_view(
            owner="intake/current_meal_read_model",
            availability=active_meal_availability,
            summary={"has_active_meal_thread": active_meal_thread_ref is not None},
        ),
        "pending_followup": _source_view(
            owner="conversation_state/intake_followup_read_model",
            availability=pending_followup_availability,
            summary={"is_open": pending_followup is not None},
        ),
        "recent_committed_meal_refs": _source_view(
            owner="committed_meal_read_model",
            availability=recent_committed_availability,
            summary={"count": len(recent_committed_meals)},
        ),
        "last_system_question": _source_view(
            owner="current_turn_runtime_summary",
            availability=last_system_question_availability,
        ),
        "current_interaction_event": _source_view(
            owner="runtime/interface_layer",
            availability="present",
            summary={
                "source": current_event.source,
                "surface_mode": current_event.surface_mode,
                "event_type": current_event.event_type,
            },
        ),
        "candidate_attachment_targets": _source_view(
            owner="phase_a_context_assembly",
            availability="present" if candidate_targets else "none",
            summary={"count": len(candidate_targets)},
        ),
    }

    context_risk_flags: list[str] = []
    if pending_followup is not None and _looks_like_ambiguous_ack(raw_user_input):
        context_risk_flags.append("ambiguous_reply_with_open_followup")
    if current_event.target_object_type != "none" and current_event.target_object_id:
        context_risk_flags.append("explicit_interaction_target")

    return CurrentTurnContextV1(
        user_utterance=raw_user_input,
        last_system_question=last_system_question,
        active_meal_thread_ref=active_meal_thread_ref,
        pending_followup=pending_followup,
        recent_committed_meal_refs=recent_committed_meals,
        current_interaction_event=current_event,
        candidate_attachment_targets=candidate_targets,
        open_workflow_type=open_workflow_type,
        context_risk_flags=context_risk_flags,
        source_views=source_views,
        current_turn_runtime_summary={
            "onboarding_ready": bool(getattr(resolved_state, "onboarding_ready", False)),
            "pending_followup_open": pending_followup is not None,
            "recent_committed_meal_count": len(recent_committed_meals),
            "target_resolution_source": str(target_meal_reference.get("target_resolution_source") or "none"),
            "has_explicit_interaction_target": bool(current_event.target_object_id),
            "surface_mode": current_event.surface_mode,
        },
    )
