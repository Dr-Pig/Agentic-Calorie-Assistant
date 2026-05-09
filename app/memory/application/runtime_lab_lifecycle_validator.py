from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.runtime_lab_lifecycle_rules import (
    default_preference_decision,
    negative_preference_decision,
    parse_as_of,
    pattern_lifecycle_decision,
    temporary_preference_decision,
    thresholds,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.runtime_lab_lifecycle_validator"
)


def validate_candidate_lifecycle(
    candidate: Mapping[str, Any],
    *,
    as_of: str,
) -> dict[str, Any]:
    as_of_dt = parse_as_of(as_of)
    candidate_type = str(candidate.get("candidate_type") or "unknown")
    auto_demote_allowed = False
    review_status_after = str(candidate.get("review_status") or "pending")

    if candidate_type in {"pattern", "golden_order"}:
        decision, reason_codes = pattern_lifecycle_decision(candidate, as_of_dt)
    elif candidate_type == "temporary_preference":
        decision, reason_codes, review_status_after = temporary_preference_decision(
            candidate,
            as_of_dt,
        )
    elif candidate_type == "negative_preference":
        decision, reason_codes, auto_demote_allowed = negative_preference_decision(
            candidate,
        )
    else:
        decision, reason_codes = default_preference_decision(candidate)

    return {
        "candidate_id": str(candidate.get("candidate_id") or "unknown_candidate"),
        "candidate_type": candidate_type,
        "decision": decision,
        "reason_codes": reason_codes,
        "thresholds": thresholds(),
        "review_status_before": str(candidate.get("review_status") or "pending"),
        "review_status_after": review_status_after,
        "promotion_allowed_now": False,
        "auto_demote_allowed": auto_demote_allowed,
        "human_review_required": True,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "canonical_mutation_changed": False,
        "manager_context_packet_changed": False,
    }


def build_lifecycle_decision_artifact(
    candidates: list[Mapping[str, Any]],
    *,
    as_of: str,
    runtime_connected: bool = False,
) -> dict[str, Any]:
    decisions = [
        validate_candidate_lifecycle(candidate, as_of=as_of) for candidate in candidates
    ]
    return {
        "artifact_type": "runtime_lab_memory_lifecycle_decisions",
        "status": "pass" if decisions else "blocked",
        "decision_count": len(decisions),
        "decisions": decisions,
        "runtime_connected": runtime_connected,
        "lab_isolated": True,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
        "manager_context_packet_changed": False,
        "shadow_memory_context_pack_used": False,
        "manager_context_injected": False,
    }


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_lifecycle_decision_artifact",
    "validate_candidate_lifecycle",
]
