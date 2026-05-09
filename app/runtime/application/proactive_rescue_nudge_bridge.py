from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "runtime.application.proactive_rescue_nudge_bridge"
)
SUPPORTED_PROJECTION = "rescue_shadow_summary_context_projection"
CLAIM_FLAGS = (
    "runtime_effect_allowed",
    "rescue_committed",
    "proposal_committed",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "durable_memory_written",
    "manager_context_injected",
    "proactive_sent",
    "recommendation_served",
)
FORBIDDEN_DETAIL_FIELDS = (
    "candidate_copy",
    "proposal_card",
    "primary_actions",
    "recommended_days",
    "daily_kcal_adjustment",
    "send_or_skip",
)
ALLOWED_HISTORY_NOTES = {
    "rescue_history_present_for_future_viability_review",
    "adherence_summary_present_for_future_viability_review",
}
NO_RESCUE_NUDGE_REVIEW = {
    "source_projection_used": False,
    "status": "not_evaluated",
    "prompt_posture": "not_applicable",
    "suppression_reasons": [],
    "blockers": [],
    "rescue_history_context_available": False,
    "adherence_context_available": False,
    "suppression_context_count": 0,
    "history_review_notes": [],
    "runtime_effect_allowed": False,
    "rescue_committed": False,
    "proposal_committed": False,
    "day_budget_mutated": False,
    "body_plan_mutated": False,
    "meal_thread_mutated": False,
    "durable_memory_written": False,
    "manager_context_injected": False,
    "proactive_sent": False,
    "recommendation_served": False,
    "scheduler_enabled": False,
    "live_delivery_allowed": False,
    "scheduler_activation_allowed": False,
}


def build_rescue_nudge_no_send_review(
    rescue_context_projection: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = _projection_blockers(rescue_context_projection)
    if blockers:
        return _review(
            rescue_context_projection,
            status="blocked",
            prompt_posture="not_applicable",
            blockers=blockers,
            reviewer_next_step="fix_rescue_context_projection_before_review",
        )
    return _review(
        rescue_context_projection,
        status="context_available",
        prompt_posture="later_only_review_context",
        blockers=[],
        reviewer_next_step="review_rescue_context_without_delivery_or_proposal",
    )


def _review(
    projection: Mapping[str, Any],
    *,
    status: str,
    prompt_posture: str,
    blockers: list[str],
    reviewer_next_step: str,
) -> dict[str, Any]:
    return {
        **dict(NO_RESCUE_NUDGE_REVIEW),
        "source_projection_used": True,
        "status": status,
        "prompt_posture": prompt_posture,
        "blockers": blockers,
        "rescue_history_context_available": bool(_mapping(projection.get("rescue_history_context"))),
        "adherence_context_available": bool(_mapping(projection.get("adherence_context"))),
        "suppression_context_count": _sequence_count(projection.get("suppression_context")),
        "history_review_notes": _history_review_notes(projection),
        "review_decision": {
            "status": "blocked" if blockers else "deferred_later_only_context_available",
            "reviewer_next_step": reviewer_next_step,
        },
    }


def _projection_blockers(projection: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if projection.get("artifact_type") != SUPPORTED_PROJECTION:
        blockers.append("rescue_context_projection.unsupported_artifact_type")
    if projection.get("status") != "pass":
        blockers.append("rescue_context_projection.status_not_pass")
    for flag in CLAIM_FLAGS:
        if projection.get(flag) is True:
            blockers.append(f"rescue_context_projection.{flag}")
    for field in FORBIDDEN_DETAIL_FIELDS:
        if _has_value(projection.get(field)):
            blockers.append(f"rescue_context_projection.{field}")
    return blockers


def _history_review_notes(projection: Mapping[str, Any]) -> list[str]:
    return [
        str(note)
        for note in projection.get("history_review_notes") or []
        if str(note) in ALLOWED_HISTORY_NOTES
    ]


def _sequence_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _has_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return value is not None


__all__ = [
    "NO_RESCUE_NUDGE_REVIEW",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_nudge_no_send_review",
]
