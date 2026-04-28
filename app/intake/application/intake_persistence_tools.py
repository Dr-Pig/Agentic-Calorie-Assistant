from __future__ import annotations

from ...database import get_or_create_user
from ...nutrition.application.estimate_artifacts import EstimatedNutritionArtifact
from .commit_service import persist_text_meal_payload
from .intake_tool_runtime import PersistMealLogResult


def persist_meal_log_tool(
    db,
    *,
    artifact: EstimatedNutritionArtifact,
    request_id: str,
) -> PersistMealLogResult:
    user = artifact.runtime_context.user or get_or_create_user(db, artifact.request.user_id)
    decision = persist_text_meal_payload(
        db=db,
        user=user,
        latest_log=artifact.runtime_context.latest_log,
        planner_intent=artifact.planner_result.intent,
        payload=artifact.payload,
        raw_input=artifact.request.text,
        request_id=request_id,
        incoming_user_message_id=artifact.runtime_context.incoming_user_message_id,
        conversation_state=artifact.runtime_context.conversation_state,
        planner_result=artifact.planner_result,
    )
    return PersistMealLogResult(
        action=str(decision.get("action") or "noop"),
        status=decision.get("status"),
        persisted_log_id=decision.get("persisted_log_id"),
        linked_meal_log_id=decision.get("linked_meal_log_id"),
        canonical_commit=decision.get("canonical_commit"),
    )
