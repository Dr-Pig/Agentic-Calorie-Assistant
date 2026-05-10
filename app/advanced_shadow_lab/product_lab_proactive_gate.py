from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_control_reducer import candidate_states
from app.advanced_shadow_lab.product_lab_proactive_gate_policy import (
    PERMISSION_POSTURE,
    context_reasons,
    permission_reasons,
    review_status,
    reviewer_next_step,
)
from app.advanced_shadow_lab.product_lab_turn_policy import observed_material_signals

def review_product_lab_proactive_candidates(
    *,
    turn: Mapping[str, Any],
    candidates: list[Mapping[str, Any]],
    prior_control_journal: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    context = _mapping(turn.get("proactive_gate_context"))
    control_states = _control_states(
        turn=turn,
        candidates=candidates,
        prior_control_journal=list(prior_control_journal or []),
    )
    reviews = [
        _review_candidate(
            turn=turn,
            context=context,
            candidate=candidate,
            control_state=control_states.get(str(candidate.get("candidate_id") or "")),
        )
        for candidate in candidates
    ]
    allowed = [
        dict(candidate)
        for candidate, review in zip(candidates, reviews, strict=False)
        if review["review_decision"]["status"] == "candidate_for_human_review"
    ]
    omissions = [_omission(review) for review in reviews if review["suppressed"]]
    return {
        "artifact_type": "advanced_product_lab_proactive_pre_delivery_review",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "candidate_review_count": len(reviews),
        "candidate_reviews": reviews,
        "allowed_candidate_count": len(allowed),
        "allowed_trigger_types": [str(item.get("trigger_type") or "") for item in allowed],
        "omission_traces": omissions,
        "summary": {"review_decision_counts": _counts(reviews)},
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
    }


def _review_candidate(
    *,
    turn: Mapping[str, Any],
    context: Mapping[str, Any],
    candidate: Mapping[str, Any],
    control_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    trigger = str(candidate.get("trigger_type") or "")
    reasons = [
        *context_reasons(turn=turn, context=context),
        *permission_reasons(trigger=trigger, context=context),
        *_control_reasons(control_state),
        *_source_reasons(candidate),
    ]
    status = review_status(reasons)
    return {
        "trigger_type": trigger,
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "permission_posture": PERMISSION_POSTURE.get(trigger, "user_expected"),
        "suppression_reasons": reasons,
        "suppressed": bool(reasons),
        "review_decision": {
            "status": status,
            "reviewer_next_step": reviewer_next_step(status),
        },
        "active_control_event_id": (
            str(control_state.get("active_control_event_id") or "")
            if control_state
            else ""
        ),
        "source_refs": [str(item) for item in candidate.get("source_output_refs") or []],
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
    }


def _control_reasons(control_state: Mapping[str, Any] | None) -> list[str]:
    if not control_state or control_state.get("visible_in_lab") is True:
        return []
    reason = str(control_state.get("suppression_reason") or "")
    return [reason] if reason else ["control_suppressed"]


def _source_reasons(candidate: Mapping[str, Any]) -> list[str]:
    return [] if candidate.get("status") == "pass" else ["source_status_not_pass"]


def _omission(review: Mapping[str, Any]) -> dict[str, Any]:
    reasons = [str(item) for item in review.get("suppression_reasons") or []]
    return {
        "trigger_type": str(review.get("trigger_type") or ""),
        "omission_reason": reasons[0] if reasons else "suppressed",
        "suppression_reasons": reasons,
        "review_decision": dict(_mapping(review.get("review_decision"))),
        "active_control_event_id": str(review.get("active_control_event_id") or ""),
        "source_refs": [str(item) for item in review.get("source_refs") or []],
        "user_facing_behavior_changed": False,
        "scheduler_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
    }


def _control_states(
    *,
    turn: Mapping[str, Any],
    candidates: list[Mapping[str, Any]],
    prior_control_journal: list[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    rows = [
        {
            "candidate_id": str(candidate.get("candidate_id") or ""),
            "trigger_type": str(candidate.get("trigger_type") or ""),
        }
        for candidate in candidates
    ]
    states = candidate_states(
        candidates=rows,
        journal=[dict(item) for item in prior_control_journal],
        lab_now_minute=int(turn.get("lab_now_minute") or 0),
        observed_material_signals=observed_material_signals(turn),
    )
    return {str(state.get("candidate_id") or ""): state for state in states}


def _counts(reviews: list[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for review in reviews:
        status = str(_mapping(review.get("review_decision")).get("status") or "")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["review_product_lab_proactive_candidates"]
