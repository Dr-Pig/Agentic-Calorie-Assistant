from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from ...shared.domain import CanonicalMealState, ConversationState


MealStatus = Literal["candidate_meal", "draft_unresolved", "completed_meal"]


def determine_meal_status(
    *,
    payload_action_taken: str,
    payload_route_target: str,
    estimated_kcal: int,
    trace_contract: dict[str, Any],
    quality_signals: dict[str, Any],
) -> MealStatus | None:
    route_family = str(trace_contract.get("route_family") or "")
    missing_slots = [str(item) for item in trace_contract.get("missing_slots", []) if str(item).strip()]
    blocking_slots = [str(item) for item in trace_contract.get("blocking_slots", []) if str(item).strip()]
    unresolved_info = [str(item) for item in trace_contract.get("unresolved_info", []) if str(item).strip()]
    has_followup = bool(trace_contract.get("followup_question")) or bool(unresolved_info)
    exact_like = str(trace_contract.get("db_hit_type") or "") == "exact_truth" or str(
        quality_signals.get("estimate_mode") or ""
    ) == "exact_item"
    response_mode_hint = str(trace_contract.get("response_mode_hint") or "")

    if payload_route_target == "clarify_user_private":
        return "draft_unresolved"
    if blocking_slots:
        return "draft_unresolved"
    if response_mode_hint == "clarify_first":
        return "draft_unresolved"
    if route_family == "component_driven_meal" and (has_followup or missing_slots):
        return "draft_unresolved"
    if payload_action_taken in {"clarify_before_estimate", "answer_with_uncertainty"} and has_followup and not exact_like:
        return "draft_unresolved"
    if estimated_kcal > 0:
        return "completed_meal"
    if has_followup or missing_slots:
        return "candidate_meal"
    return None


def active_meal_context_allowed(
    meal_id: int | None,
    meal_title: str,
    status: MealStatus,
    components: list[dict[str, Any]] | None = None,
    pending_questions: list[str] | None = None,
    unresolved_info: list[str] | None = None,
    followup_count: int = 0,
    asked_questions_history: list[str] | None = None,
    last_followup_key: str | None = None,
    boundary_history: list[str] | None = None,
    last_updated_at: datetime | None = None,
    source_log_ids: list[int] | None = None,
) -> CanonicalMealState:
    return CanonicalMealState(
        meal_id=meal_id,
        meal_title=meal_title,
        status=status,
        components=components or [],
        pending_questions=pending_questions or [],
        unresolved_info=unresolved_info or [],
        followup_count=max(0, int(followup_count or 0)),
        asked_questions_history=asked_questions_history or [],
        last_followup_key=last_followup_key,
        boundary_history=boundary_history or [],
        last_updated_at=last_updated_at,
        source_log_ids=source_log_ids or ([meal_id] if meal_id is not None else []),
    )


def canonical_meal_state_from_runtime(
    *,
    latest_log: Any | None,
    state: ConversationState,
    normalize_text: Any,
) -> CanonicalMealState | None:
    if latest_log is None and not state.active_meal_summary.meal_title:
        return None
    meal_id = int(latest_log.id) if latest_log is not None and getattr(latest_log, "id", None) is not None else None
    meal_title = str(
        (latest_log.meal_title if latest_log is not None else "") or state.active_meal_summary.meal_title or ""
    )
    pending: list[str] = []
    if latest_log is not None and getattr(latest_log, "pending_question", None):
        pending.append(str(latest_log.pending_question))
    elif state.pending_question:
        pending.append(str(state.pending_question))
    elif state.planner_state_digest.pending_question:
        pending.append(str(state.planner_state_digest.pending_question))
    unresolved_info = [
        str(item) for item in state.active_meal_summary.unresolved_slots if str(item).strip()
    ]
    asked_questions_history = [
        normalize_text(message.content)
        for message in state.recent_messages
        if str(message.role) == "assistant" and str(message.content or "").strip().endswith("?")
    ]
    last_followup_key = asked_questions_history[-1] if asked_questions_history else None
    followup_count = asked_questions_history.count(last_followup_key) if last_followup_key else 0
    status = "draft_unresolved" if pending or unresolved_info else "completed_meal"
    components = list(getattr(latest_log, "components_json", None) or []) if latest_log is not None else []
    return active_meal_context_allowed(
        meal_id=meal_id,
        meal_title=meal_title,
        status=status,  # type: ignore[arg-type]
        components=components,
        pending_questions=pending,
        unresolved_info=unresolved_info,
        followup_count=followup_count,
        asked_questions_history=asked_questions_history,
        last_followup_key=last_followup_key,
        boundary_history=[str(state.active_meal_summary.meal_title or "")] if state.active_meal_summary.meal_title else [],
        last_updated_at=getattr(latest_log, "updated_at", None) if latest_log is not None else None,
        source_log_ids=[meal_id] if meal_id is not None else [],
    )


def build_boundary_trace(
    *,
    state: ConversationState,
    active_meal_context_allowed: bool,
    confidence_signals: dict[str, Any] | None = None,
    downgrade_reasons: list[str] | None = None,
) -> dict[str, Any]:
    signals = confidence_signals or {}
    resolution_state = "open" if state.boundary_clarification_open else "not_applicable"
    return {
        "meal_boundary": signals.get("meal_boundary"),
        "manager_self_reported_confidence": signals.get("manager_self_reported_confidence"),
        "calibrated_confidence": signals.get("calibrated_confidence"),
        "active_meal_id": state.latest_log_id,
        "active_meal_status": state.latest_log_status,
        "pending_question_present": bool(state.pending_question),
        "retrieved_transcript_chunk_ids": [chunk.chunk_id for chunk in state.retrieved_transcript_chunks],
        "retrieved_meal_log_ids": [chunk.chunk_id for chunk in state.retrieved_meal_records],
        "time_gap_seconds": state.active_meal_time_gap_seconds,
        "active_meal_context_allowed": active_meal_context_allowed,
        "boundary_followup_triggered": bool(signals.get("boundary_followup_triggered")) or resolution_state == "open",
        "boundary_resolution_state": resolution_state,
        "boundary_resolution_source_meal_id": state.boundary_clarification_source_meal_id,
        "confidence_signals": signals,
        "downgrade_reasons": downgrade_reasons or [],
        "retrieval_diagnostics": state.retrieval_diagnostics,
    }
