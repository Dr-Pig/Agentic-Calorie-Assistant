from __future__ import annotations

from ...runtime.contracts.phase_a import (
    AttachmentDecision,
    CurrentTurnContextV1,
    TransitionGuardResult,
)


def resolve_transition_guard(
    current_turn_context: CurrentTurnContextV1,
    attachment_decision: AttachmentDecision,
) -> TransitionGuardResult:
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
