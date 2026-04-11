from __future__ import annotations

from typing import Any

from ..application.text_meal_commit_service import persist_text_meal_payload
from ..schemas import EstimatePayload


def apply_persistence_decision(
    *,
    db: Any,
    user: Any,
    latest_log: Any,
    planner_intent: str,
    payload: EstimatePayload,
    raw_input: str,
    request_id: str,
    incoming_user_message_id: int | None,
    conversation_state: Any,
    planner_result: Any,
) -> dict[str, Any]:
    return persist_text_meal_payload(
        db=db,
        user=user,
        latest_log=latest_log,
        planner_intent=planner_intent,
        payload=payload,
        raw_input=raw_input,
        request_id=request_id,
        incoming_user_message_id=incoming_user_message_id,
        conversation_state=conversation_state,
        planner_result=planner_result,
    )
