from __future__ import annotations

from typing import Any

from ...shared.domain import ActiveMealState, ActiveMealSummary, ConversationDigest
from ...shared.time_labels import describe_time_fields


def build_active_meal_summary(*, latest_log: Any | None, conversation_digest: ConversationDigest) -> ActiveMealSummary:
    debug_steps = list(latest_log.debug_steps_json or []) if latest_log else []
    selected_evidence_titles: list[str] = []
    for step in debug_steps:
        title = step.get("reference_title") or step.get("evidence_title")
        if title and title not in selected_evidence_titles:
            selected_evidence_titles.append(str(title))
    accepted_corrections = []
    if conversation_digest.last_explicit_correction:
        accepted_corrections.append(conversation_digest.last_explicit_correction)
    return ActiveMealSummary(
        meal_title=latest_log.meal_title if latest_log else None,
        status=latest_log.status if latest_log else None,
        unresolved_slots=[latest_log.pending_question] if latest_log and latest_log.pending_question else [],
        accepted_corrections=accepted_corrections,
        selected_evidence_titles=selected_evidence_titles[:3],
    )


def build_active_meal_state(*, latest_log: Any | None, conversation_digest: ConversationDigest) -> ActiveMealState:
    if latest_log is None:
        return ActiveMealState()
    time_fields = describe_time_fields(latest_log.timestamp.isoformat() if latest_log.timestamp else None)
    debug_steps = list(latest_log.debug_steps_json or [])
    trace_contract = next(
        (
            dict(step.get("trace_contract") or {})
            for step in reversed(debug_steps)
            if isinstance(step, dict) and step.get("trace_contract")
        ),
        {},
    )
    return ActiveMealState(
        meal_id=latest_log.id,
        meal_title=latest_log.meal_title,
        status=latest_log.status,
        estimate_mode=str(trace_contract.get("best_estimate_mode") or "") or None,
        confidence=str(trace_contract.get("estimate_confidence_tier") or "") or None,
        pending_question=latest_log.pending_question,
        missing_slots=[latest_log.pending_question] if latest_log.pending_question else [],
        resolved_slots=[],
        resolved_food_items=[
            str(item.get("name") or "")
            for item in list(latest_log.components_json or [])
            if str(item.get("name") or "").strip()
        ],
        accepted_corrections=[conversation_digest.last_explicit_correction] if conversation_digest.last_explicit_correction else [],
        relative_time_label=time_fields.get("relative_time_label") or None,
        local_date=time_fields.get("local_date") or None,
    )
