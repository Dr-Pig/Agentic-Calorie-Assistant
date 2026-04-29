from __future__ import annotations

from ...runtime.contracts.phase_a import ShadowHypothesis


def _default_shadow_visibility(confidence: str) -> str:
    return "internal_only" if confidence == "high" else "uncertainty_visible"


def build_shadow_hypothesis(
    *,
    hypothesis_id: str,
    target_object_type: str,
    target_object_id: str | None,
    intent: str,
    confidence: str,
    created_from: str,
    visibility_posture: str | None = None,
    expires_on: str | None = None,
    invalidation_reasons: list[str] | None = None,
) -> ShadowHypothesis:
    return ShadowHypothesis(
        hypothesis_id=hypothesis_id,
        target_object_type=target_object_type,
        target_object_id=target_object_id,
        intent=intent,
        confidence=confidence,
        visibility_posture=visibility_posture or _default_shadow_visibility(confidence),
        created_from=created_from,
        expires_on=expires_on,
        invalidation_reasons=list(invalidation_reasons or []),
        mutation_authority=False,
    )


def _shadow_invalidation_reason(
    *,
    resolved: bool = False,
    contradicted: bool = False,
    topic_reset: bool = False,
    workflow_switched: bool = False,
    idle_expired: bool = False,
) -> str | None:
    if resolved:
        return "resolved"
    if contradicted:
        return "contradicted"
    if topic_reset:
        return "topic_reset"
    if workflow_switched:
        return "workflow_switched"
    if idle_expired:
        return "idle_expired"
    return None


def advance_shadow_hypothesis(
    hypothesis: ShadowHypothesis,
    *,
    resolved: bool = False,
    contradicted: bool = False,
    topic_reset: bool = False,
    workflow_switched: bool = False,
    idle_expired: bool = False,
) -> ShadowHypothesis | None:
    invalidation_reason = _shadow_invalidation_reason(
        resolved=resolved,
        contradicted=contradicted,
        topic_reset=topic_reset,
        workflow_switched=workflow_switched,
        idle_expired=idle_expired,
    )
    if invalidation_reason is not None:
        return None
    return hypothesis
