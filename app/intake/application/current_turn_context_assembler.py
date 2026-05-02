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


def _current_budget_snapshot(payload: Any, *, has_active_plan: bool) -> dict[str, Any] | None:
    budget = _as_dict(payload)
    if not budget:
        return None
    return {
        "local_date": budget.get("local_date"),
        "budget_kcal": int(budget.get("budget_kcal") or 0),
        "consumed_kcal": int(budget.get("consumed_kcal") or 0),
        "remaining_kcal": int(budget.get("remaining_kcal") or 0),
        "active_meal_count": int(budget.get("active_meal_count") or 0),
        "has_active_plan": bool(budget.get("has_active_plan") if "has_active_plan" in budget else has_active_plan),
        "has_day_budget_ledger": bool(budget.get("has_day_budget_ledger", False)),
        "ledger_last_recomputed_at": budget.get("ledger_last_recomputed_at"),
        "no_plan_posture": str(budget.get("no_plan_posture") or "not_applicable"),
        "overshoot_status": str(budget.get("overshoot_status") or "unknown"),
        "freshness_status": str(budget.get("freshness_status") or "current_turn"),
        "source": "current_budget_view",
        "truth_owner": "budget_read_model",
        "read_only": True,
    }


def _active_body_plan_snapshot(payload: Any) -> dict[str, Any] | None:
    body_plan = _as_dict(payload)
    if not body_plan:
        return None
    return {
        "body_plan_id": body_plan.get("body_plan_id"),
        "goal_type": body_plan.get("goal_type"),
        "daily_budget_kcal": int(body_plan.get("daily_budget_kcal") or 0),
        "estimated_tdee": int(body_plan.get("estimated_tdee") or 0),
        "safety_floor_kcal": int(body_plan.get("safety_floor_kcal") or 0),
        "freshness_status": str(body_plan.get("freshness_status") or "current_turn"),
        "source": "active_body_plan_view",
        "truth_owner": "body_read_model",
        "read_only": True,
    }


def _recent_item_targets(
    *,
    target_meal_reference: dict[str, Any],
    recent_committed_meals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    if target_meal_reference.get("meal_item_id") is None:
        pass
    else:
        targets.append(
            {
                "target_object_type": "meal_item",
                "meal_thread_id": target_meal_reference.get("meal_thread_id"),
                "meal_version_id": target_meal_reference.get("meal_version_id"),
                "meal_item_id": target_meal_reference.get("meal_item_id"),
                "canonical_name": target_meal_reference.get("canonical_name"),
                "source": str(target_meal_reference.get("target_resolution_source") or "target_meal_reference"),
                "confidence": str(target_meal_reference.get("correction_confidence") or "medium"),
                "item_resolution_source": str(target_meal_reference.get("item_resolution_source") or "unknown"),
            }
        )
    for meal in recent_committed_meals:
        item_resolution_source = str(meal.get("item_resolution_source") or "unknown")
        for candidate in list(meal.get("item_candidates") or []):
            if not isinstance(candidate, dict):
                continue
            targets.append(
                {
                    "target_object_type": "meal_item_candidate",
                    "meal_thread_id": meal.get("meal_thread_id"),
                    "meal_version_id": meal.get("meal_version_id"),
                    "meal_item_id": candidate.get("meal_item_id"),
                    "canonical_name": candidate.get("canonical_name"),
                    "item_index": candidate.get("item_index"),
                    "estimated_kcal": int(candidate.get("estimated_kcal") or 0),
                    "source": "recent_committed_meal",
                    "confidence": "medium",
                    "item_resolution_source": item_resolution_source,
                    "mutation_authority": False,
                    "selected_target": False,
                }
            )
    return targets


def _target_resolution_posture(target_meal_reference: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_resolution_source": str(target_meal_reference.get("target_resolution_source") or "none"),
        "correction_confidence": str(target_meal_reference.get("correction_confidence") or "low"),
        "item_resolution_source": str(target_meal_reference.get("item_resolution_source") or "none"),
        "mutation_authority": False,
        "read_only": True,
    }


def _session_atomic_blocks(
    *,
    raw_user_input: str,
    last_system_question: str | None,
    pending_followup: dict[str, Any] | None,
    target_meal_reference: dict[str, Any],
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    if last_system_question:
        blocks.append(
            {
                "block_type": "clarification_question_answer",
                "role": "support_evidence",
                "read_only": True,
                "mutation_authority": False,
                "question": last_system_question,
                "answer": raw_user_input,
                "object_ref": {"meal_thread_id": pending_followup.get("meal_thread_id") if pending_followup else None},
            }
        )
    if pending_followup is not None:
        blocks.append(
            {
                "block_type": "pending_followup",
                "role": "support_evidence",
                "read_only": True,
                "mutation_authority": False,
                "pending_question": pending_followup.get("pending_question") or pending_followup.get("question"),
                "object_ref": {"meal_thread_id": pending_followup.get("meal_thread_id")},
            }
        )
    if target_meal_reference.get("meal_thread_id") is not None:
        object_ref = {
            "meal_thread_id": target_meal_reference.get("meal_thread_id"),
            "meal_version_id": target_meal_reference.get("meal_version_id"),
        }
        if target_meal_reference.get("meal_item_id") is not None:
            object_ref["meal_item_id"] = target_meal_reference.get("meal_item_id")
        if target_meal_reference.get("canonical_name") is not None:
            object_ref["canonical_name"] = target_meal_reference.get("canonical_name")
        blocks.append(
            {
                "block_type": "correction_target_reference",
                "role": "support_evidence",
                "read_only": True,
                "mutation_authority": False,
                "object_ref": object_ref,
                "target_resolution_source": str(target_meal_reference.get("target_resolution_source") or "none"),
                "item_resolution_source": str(target_meal_reference.get("item_resolution_source") or "none"),
            }
        )
    return blocks


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
                "mutation_authority": False,
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
    budget_payload = injected_context.get("CURRENT_BUDGET")
    active_body_plan_payload = injected_context.get("ACTIVE_BODY_PLAN")
    target_meal_reference = _as_dict(injected_context.get("TARGET_MEAL_REFERENCE"))
    session_summary = _as_dict(injected_context.get("SESSION_SUMMARY"))

    last_system_question, last_system_question_availability = _last_system_question(
        resolved_state=resolved_state,
        session_summary=session_summary,
    )
    active_meal_thread_ref, active_meal_availability = _active_meal_thread_state(active_meal)
    pending_followup, pending_followup_availability = _pending_followup_state(_as_dict(pending_followup_payload))
    recent_committed_meals, recent_committed_availability = _recent_committed_state(recent_meals_payload)
    current_budget_snapshot = _current_budget_snapshot(
        budget_payload,
        has_active_plan=bool(getattr(resolved_state, "onboarding_ready", False))
        or _as_dict(active_body_plan_payload).get("body_plan_id") is not None,
    )
    active_body_plan_snapshot = _active_body_plan_snapshot(active_body_plan_payload)
    recent_item_targets = _recent_item_targets(
        target_meal_reference=target_meal_reference,
        recent_committed_meals=recent_committed_meals,
    )
    target_resolution_posture = _target_resolution_posture(target_meal_reference)
    session_atomic_blocks = _session_atomic_blocks(
        raw_user_input=raw_user_input,
        last_system_question=last_system_question,
        pending_followup=pending_followup,
        target_meal_reference=target_meal_reference,
    )
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
        "current_budget_snapshot": _source_view(
            owner="budget/current_budget_read_model",
            availability="present" if current_budget_snapshot is not None else "unknown",
            summary={"read_only": True},
        ),
        "active_body_plan_snapshot": _source_view(
            owner="body/active_body_plan_read_model",
            availability="present" if active_body_plan_snapshot is not None else "unknown",
            summary={"read_only": True},
        ),
        "recent_item_targets": _source_view(
            owner="intake/correction_target_read_model",
            availability="present" if recent_item_targets else "none",
            summary={"count": len(recent_item_targets), "read_only": True},
        ),
        "session_atomic_blocks": _source_view(
            owner="conversation_state/current_session_summary",
            availability="present" if session_atomic_blocks else "none",
            summary={"count": len(session_atomic_blocks), "read_only": True},
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
        current_budget_snapshot=current_budget_snapshot,
        active_body_plan_snapshot=active_body_plan_snapshot,
        recent_item_targets=recent_item_targets,
        target_resolution_posture=target_resolution_posture,
        context_freshness={
            "current_budget_snapshot": (
                str(current_budget_snapshot.get("freshness_status") or "unknown")
                if current_budget_snapshot is not None
                else "unknown"
            ),
            "active_body_plan_snapshot": (
                str(active_body_plan_snapshot.get("freshness_status") or "unknown")
                if active_body_plan_snapshot is not None
                else "unknown"
            ),
            "recent_item_targets": "current_turn" if recent_item_targets else "none",
            "session_atomic_blocks": "current_turn" if session_atomic_blocks else "none",
        },
        session_atomic_blocks=session_atomic_blocks,
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
            "has_current_budget_snapshot": current_budget_snapshot is not None,
            "has_active_body_plan_snapshot": active_body_plan_snapshot is not None,
            "recent_item_target_count": len(recent_item_targets),
            "session_atomic_block_count": len(session_atomic_blocks),
        },
    )
