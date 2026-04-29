from __future__ import annotations

from typing import Any

from ...runtime.contracts.phase_a import (
    AttachmentDecision,
    CurrentTurnContextV1,
    TransitionGuardResult,
)


def build_phase_a_trace(
    *,
    current_turn_context: CurrentTurnContextV1,
    attachment_decision: AttachmentDecision,
    transition_guard_result: TransitionGuardResult,
    history_expansion_activation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "current_turn_context": current_turn_context.model_dump(mode="json"),
        "interaction_event": current_turn_context.current_interaction_event.model_dump(mode="json"),
        "attachment_decision": attachment_decision.model_dump(mode="json"),
        "transition_guard_result": transition_guard_result.model_dump(mode="json"),
    }
    if history_expansion_activation is not None:
        payload["history_expansion_activation"] = history_expansion_activation
    return payload
