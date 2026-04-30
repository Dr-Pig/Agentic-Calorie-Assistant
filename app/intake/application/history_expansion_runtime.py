from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...runtime.contracts.phase_a import (
    AttachmentDecision,
    CurrentTurnContextV1,
    HistoryExpansionRequest,
    HistoryExpansionResult,
    TransitionGuardResult,
)
from .attachment_resolver import resolve_attachment_decision
from .transition_guard import resolve_transition_guard


@dataclass(frozen=True)
class HistoryExpansionActivationResult:
    applied: bool
    request: HistoryExpansionRequest | None
    result: HistoryExpansionResult | None
    atomic_blocks_status: str
    pre_attachment_decision: AttachmentDecision
    pre_transition_guard_result: TransitionGuardResult
    post_attachment_decision: AttachmentDecision
    post_transition_guard_result: TransitionGuardResult
    enriched_current_turn_context: CurrentTurnContextV1
    resolution_gain: bool
    selected_candidate_ids: tuple[str, ...] = ()
    ambiguity_detected: bool = False
    transcript_support_inventory: tuple[str, ...] = ()

    def trace_payload(self) -> dict[str, Any]:
        result_summary = None
        if self.result is not None:
            result_summary = {
                "meal_candidate_count": len(self.result.meal_candidates),
                "atomic_block_count": len(self.result.atomic_blocks),
                "transcript_support_count": len(self.result.transcript_snippets),
            }
        return {
            "triggered": self.applied,
            "reason": self.request.reason if self.request is not None else None,
            "scope": self.request.scope if self.request is not None else None,
            "request": self.request.model_dump(mode="json") if self.request is not None else None,
            "result_summary": result_summary,
            "atomic_blocks_status": self.atomic_blocks_status,
            "pre_decision": self.pre_attachment_decision.model_dump(mode="json"),
            "post_decision": self.post_attachment_decision.model_dump(mode="json"),
            "resolution_gain": self.resolution_gain,
            "selected_candidate_ids": list(self.selected_candidate_ids),
            "ambiguity_detected": self.ambiguity_detected,
            "transcript_support_inventory": list(self.transcript_support_inventory),
        }


def activate_pre_manager_history_expansion(
    *,
    current_turn_context: CurrentTurnContextV1,
    resolved_state: Any,
    pre_attachment_decision: AttachmentDecision | None = None,
    pre_transition_guard_result: TransitionGuardResult | None = None,
) -> HistoryExpansionActivationResult:
    pre_attachment = pre_attachment_decision or resolve_attachment_decision(current_turn_context)
    pre_guard = pre_transition_guard_result or resolve_transition_guard(current_turn_context, pre_attachment)
    return HistoryExpansionActivationResult(
        applied=False,
        request=None,
        result=None,
        atomic_blocks_status="trace_only_disabled",
        pre_attachment_decision=pre_attachment,
        pre_transition_guard_result=pre_guard,
        post_attachment_decision=pre_attachment,
        post_transition_guard_result=pre_guard,
        enriched_current_turn_context=current_turn_context,
        resolution_gain=False,
    )


__all__ = [
    "HistoryExpansionActivationResult",
    "activate_pre_manager_history_expansion",
]
