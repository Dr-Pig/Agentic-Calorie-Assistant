from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_records import scope_keys
from app.recommendation.application.feedback_event_projection import (
    LAB_FEEDBACK_ACTIONS,
    build_recommendation_offer_feedback_target,
)


def recommendation_feedback_fields(
    *,
    turn: Mapping[str, Any],
    primary_candidate: Mapping[str, Any],
) -> dict[str, Any]:
    feedback_target = build_recommendation_offer_feedback_target(
        turn_id=str(turn.get("turn_id") or ""),
        scope_keys=scope_keys(str(turn.get("session_id") or "")),
        primary_candidate=primary_candidate,
    )
    return {
        "feedback_target": feedback_target,
        "feedback_actions": list(LAB_FEEDBACK_ACTIONS),
        "feedback_event_projection_ready": not bool(feedback_target.get("blockers")),
    }


__all__ = ["recommendation_feedback_fields"]
