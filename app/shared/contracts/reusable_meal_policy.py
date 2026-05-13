from __future__ import annotations

from typing import Any, Mapping


def evaluate_reusable_meal_policy(
    *,
    repetition_count: int,
    explicit_same_as_before: bool,
    ingredient_drift: bool,
    portion_drift: bool,
    source_drift: bool,
    correction_count: int,
) -> dict[str, Any]:
    drift_flags = {
        "ingredient_drift": ingredient_drift,
        "portion_drift": portion_drift,
        "source_drift": source_drift,
    }
    if any(drift_flags.values()):
        decision = "re_estimate_required"
    elif explicit_same_as_before and correction_count == 0 and repetition_count >= 3:
        decision = "reuse_exact"
    elif repetition_count >= 3:
        decision = "reuse_anchored"
    else:
        decision = "candidate_only"
    promote_candidate = repetition_count >= 3 or explicit_same_as_before
    return {
        "artifact_type": "shared_reusable_meal_policy_evaluation",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "decision": decision,
        "promote_candidate": promote_candidate,
        "drift_flags": drift_flags,
        "repetition_count": repetition_count,
        "explicit_same_as_before": explicit_same_as_before,
        "correction_count": correction_count,
        "blockers": [],
    }


def build_reusable_meal_policy_contract() -> dict[str, Any]:
    return {
        "artifact_type": "shared_reusable_meal_policy_contract",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "allowed_decisions": [
            "candidate_only",
            "reuse_exact",
            "reuse_anchored",
            "re_estimate_required",
        ],
        "candidate_threshold_repetition_count": 3,
        "exact_reuse_requires_explicit_same_as_before": True,
        "drift_forces_reestimate": True,
        "blockers": [],
    }


__all__ = [
    "build_reusable_meal_policy_contract",
    "evaluate_reusable_meal_policy",
]
