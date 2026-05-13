from __future__ import annotations

from typing import Any, Mapping


SUPPORTED_ARTIFACT = "rescue_feedback_memory_projection"
DISMISS_SUBTYPE = "dismissed_rescue_instance"


def rescue_feedback_omission_trace(
    feedback_projection: Mapping[str, Any],
) -> dict[str, Any] | None:
    if (
        feedback_projection.get("artifact_type") != SUPPORTED_ARTIFACT
        or feedback_projection.get("status") != "pass"
    ):
        return None
    candidate = _dismiss_candidate(feedback_projection)
    if candidate is None:
        return None
    return {
        "trigger_type": "rescue_nudge",
        "omission_reason": "rescue_feedback_dismissal_pending_review",
        "source_refs": [str(ref) for ref in candidate.get("source_object_refs") or []],
        "source_candidate_id": str(candidate.get("candidate_id") or ""),
        "review_status": str(candidate.get("review_status") or ""),
        "human_review_required": candidate.get("human_review_required") is True,
        "memory_truth_claimed": candidate.get("memory_truth_claimed") is True,
        "next_signal_required": "material_budget_change_or_user_reopens_rescue",
        "user_facing_behavior_changed": False,
        "scheduler_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
    }


def _dismiss_candidate(
    feedback_projection: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    for candidate in feedback_projection.get("reviewed_memory_candidates") or []:
        if not isinstance(candidate, Mapping):
            continue
        payload = _mapping(candidate.get("payload"))
        if payload.get("rescue_memory_subtype") == DISMISS_SUBTYPE:
            return candidate
    return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["rescue_feedback_omission_trace"]
