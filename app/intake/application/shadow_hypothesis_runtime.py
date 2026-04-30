from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...runtime.contracts.phase_a import (
    AttachmentDecision,
    CurrentTurnContextV1,
    ShadowHypothesis,
    TransitionGuardResult,
)
from .shadow_hypothesis import build_shadow_hypothesis


@dataclass(frozen=True)
class ShadowHypothesisRuntimeResult:
    created: bool
    skip_reason: str | None
    hypothesis: ShadowHypothesis | None
    manager_payload: dict[str, Any] | None
    current_turn_context: CurrentTurnContextV1
    attachment_decision: AttachmentDecision
    transition_guard_result: TransitionGuardResult

    def trace_payload(self) -> dict[str, Any]:
        payload = self.manager_payload or {}
        return {
            "created": self.created,
            "skip_reason": self.skip_reason,
            "role": payload.get("role"),
            "candidate_target_object_type": payload.get("candidate_target_object_type"),
            "candidate_target_object_id": payload.get("candidate_target_object_id"),
            "intent": payload.get("candidate_intent"),
            "confidence": payload.get("confidence"),
            "visibility_posture": payload.get("visibility_posture"),
            "mutation_authority": payload.get("mutation_authority", False),
        }


def _candidate_targets(current_turn_context: CurrentTurnContextV1) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for target in current_turn_context.candidate_attachment_targets:
        if not isinstance(target, dict):
            continue
        target_type = str(target.get("target_object_type") or "")
        target_id = str(target.get("target_object_id") or "").strip()
        if target_type != "meal_thread" or not target_id or target_id in seen:
            continue
        seen.add(target_id)
        deduped.append(dict(target))
    return deduped


def _skip_reason(
    *,
    current_turn_context: CurrentTurnContextV1,
    attachment_decision: AttachmentDecision,
    transition_guard_result: TransitionGuardResult,
    candidates: list[dict[str, Any]],
) -> str | None:
    event = current_turn_context.current_interaction_event
    if event.surface_mode != "chat_freeform":
        return "explicit_ui_target"
    if event.target_object_id:
        return "explicit_ui_target"
    if event.target_object_type == "proposal" or current_turn_context.open_workflow_type == "proposal":
        return "non_meal_primary_route"
    if (
        current_turn_context.pending_followup is not None
        and attachment_decision.target_object_id is not None
        and transition_guard_result.verdict == "pass"
    ):
        return "resolved_pending_followup"
    if transition_guard_result.verdict == "pass":
        return "already_safe_pass"
    if not candidates:
        return "no_plausible_target"
    if len(candidates) > 1:
        return "multiple_plausible_targets"
    return None


def _manager_payload(hypothesis: ShadowHypothesis) -> dict[str, Any]:
    return {
        "role": "tentative_non_authoritative",
        "hypothesis_id": hypothesis.hypothesis_id,
        "candidate_target_object_type": hypothesis.target_object_type,
        "candidate_target_object_id": hypothesis.target_object_id,
        "candidate_intent": hypothesis.intent,
        "confidence": hypothesis.confidence,
        "visibility_posture": hypothesis.visibility_posture,
        "created_from": hypothesis.created_from,
        "expires_on": hypothesis.expires_on,
        "invalidation_reasons": list(hypothesis.invalidation_reasons),
        "mutation_authority": False,
    }


def build_shadow_hypothesis_runtime(
    *,
    current_turn_context: CurrentTurnContextV1,
    attachment_decision: AttachmentDecision,
    transition_guard_result: TransitionGuardResult,
) -> ShadowHypothesisRuntimeResult:
    candidates = _candidate_targets(current_turn_context)
    skip_reason = _skip_reason(
        current_turn_context=current_turn_context,
        attachment_decision=attachment_decision,
        transition_guard_result=transition_guard_result,
        candidates=candidates,
    )
    if skip_reason is not None:
        return ShadowHypothesisRuntimeResult(
            created=False,
            skip_reason=skip_reason,
            hypothesis=None,
            manager_payload=None,
            current_turn_context=current_turn_context,
            attachment_decision=attachment_decision,
            transition_guard_result=transition_guard_result,
        )

    selected = candidates[0]
    selected_id = str(selected["target_object_id"])
    selected_type = str(selected.get("target_object_type") or "meal_thread")
    intent = "manager_review_required"
    hypothesis = build_shadow_hypothesis(
        hypothesis_id=f"phase_a_shadow:{selected_type}:{selected_id}:{intent}",
        target_object_type=selected_type,
        target_object_id=selected_id,
        intent=str(intent),
        confidence=str(selected.get("confidence") or "medium"),
        created_from="phase_a_shadow_hypothesis_runtime",
        visibility_posture="uncertainty_visible",
    )
    return ShadowHypothesisRuntimeResult(
        created=True,
        skip_reason=None,
        hypothesis=hypothesis,
        manager_payload=_manager_payload(hypothesis),
        current_turn_context=current_turn_context,
        attachment_decision=attachment_decision,
        transition_guard_result=transition_guard_result,
    )


__all__ = [
    "ShadowHypothesisRuntimeResult",
    "build_shadow_hypothesis_runtime",
]
