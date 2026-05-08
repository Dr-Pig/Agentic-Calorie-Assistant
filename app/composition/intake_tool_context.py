from __future__ import annotations

from typing import Any

from app.shared.contracts.correction_target import validate_correction_target_ref


def contextualized_query_for_estimation(*, raw_user_input: str, state_before: Any) -> str | None:
    pending_followup = ((state_before.injected_context or {}).get("PENDING_FOLLOWUP") or {})
    if not bool(pending_followup.get("is_open")):
        return None
    target = ((state_before.injected_context or {}).get("TARGET_MEAL_REFERENCE") or {})
    meal_title = str(target.get("meal_title") or "").strip()
    pending_question = str(pending_followup.get("pending_question") or "").strip()
    answer = str(raw_user_input or "").strip()
    if not meal_title or not answer:
        return None
    if pending_question:
        return f"Follow-up for {meal_title}. Pending question: {pending_question} User answer: {answer}"
    return f"Follow-up for {meal_title}: {answer}"


def correction_target_resolved(correction_target: dict[str, Any]) -> bool:
    return validate_correction_target_ref(correction_target).get("resolved") is True
