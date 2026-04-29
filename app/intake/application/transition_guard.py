from __future__ import annotations

from ...runtime.agent.manager_fallback_policy import looks_like_correction
from ...runtime.contracts.phase_a import (
    AttachmentDecision,
    CurrentTurnContextV1,
    TransitionGuardResult,
)


def resolve_transition_guard(
    current_turn_context: CurrentTurnContextV1,
    attachment_decision: AttachmentDecision,
) -> TransitionGuardResult:
    if looks_like_correction(current_turn_context.user_utterance) and attachment_decision.target_object_id is None:
        return TransitionGuardResult(
            verdict="clarify_required",
            reason="correction_target_unknown",
            blocked_mutation="correction",
            affected_object_type="meal_thread",
            affected_object_id=None,
        )
    if attachment_decision.disposition == "answer_only":
        return TransitionGuardResult(
            verdict="answer_only",
            reason="no_state_mutation_allowed",
            blocked_mutation="meal_mutation",
            affected_object_type="none",
            affected_object_id=None,
        )
    return TransitionGuardResult(
        verdict="pass",
        reason="phase_a_attachment_allowed",
        blocked_mutation=None,
        affected_object_type=attachment_decision.target_object_type,
        affected_object_id=attachment_decision.target_object_id,
    )
