from __future__ import annotations

from ...database import get_or_create_user
from ...nutrition.application.estimate_artifacts import EstimatedNutritionArtifact
from .commit_service import persist_text_meal_payload
from .intake_tool_runtime import PersistMealLogResult


def _manager_intent_from_semantic_decision(
    *,
    manager_semantic_decision: dict | None,
    final_action: str | None,
) -> str:
    decision = dict(manager_semantic_decision or {})
    current_turn_intent = str(decision.get("current_turn_intent") or "").strip()
    if final_action == "correction_applied" or current_turn_intent == "correct_meal":
        return "modification"
    return current_turn_intent or "unknown"


def persist_meal_log_tool(
    db,
    *,
    artifact: EstimatedNutritionArtifact,
    request_id: str,
    final_action: str | None = None,
    manager_semantic_decision: dict | None = None,
) -> PersistMealLogResult:
    user = artifact.runtime_context.user or get_or_create_user(db, artifact.request.user_id)
    manager_intent = _manager_intent_from_semantic_decision(
        manager_semantic_decision=manager_semantic_decision,
        final_action=final_action,
    )
    decision = persist_text_meal_payload(
        db=db,
        user=user,
        latest_log=artifact.runtime_context.latest_log,
        manager_intent=manager_intent,
        payload=artifact.payload,
        raw_input=artifact.request.text,
        request_id=request_id,
        incoming_user_message_id=artifact.runtime_context.incoming_user_message_id,
        conversation_state=artifact.runtime_context.conversation_state,
        manager_semantic_decision=manager_semantic_decision,
    )
    return PersistMealLogResult(
        action=str(decision.get("action") or "noop"),
        status=decision.get("status"),
        persisted_log_id=decision.get("persisted_log_id"),
        linked_meal_log_id=decision.get("linked_meal_log_id"),
        canonical_commit=decision.get("canonical_commit"),
    )
