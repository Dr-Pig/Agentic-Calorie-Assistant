from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.runtime_lab_downstream_boundary import (
    consumer_summary_projection_blockers,
)
from app.rescue.domain.shadow_status import RESCUE_SHADOW_NON_RUNTIME_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.shadow_summary_context"
)
NON_CLAIMS = [
    "not_rescue_invitation",
    "not_rescue_proposal",
    "not_rescue_commit",
    "not_proactive_send_or_skip_decision",
    "not_manager_context_packet_input",
    "not_durable_memory_truth",
]


def build_rescue_shadow_summary_context_projection(
    *,
    memory_summary_projection: Mapping[str, Any],
    derived_memory_views: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = consumer_summary_projection_blockers(memory_summary_projection)
    status = "blocked" if blockers else "pass"
    return {
        "artifact_type": "rescue_shadow_summary_context_projection",
        "status": status,
        "blockers": blockers,
        "owner": "app/rescue",
        "consumer": "future rescue/proactive shadow review slices",
        "retirement_trigger": "approved rescue_runtime_activation_plan",
        "memory_summary_projection_used": status == "pass",
        "memory_signal_summary": {}
        if blockers
        else _memory_signal_summary(memory_summary_projection),
        "suppression_context": []
        if blockers
        else _suppression_context(memory_summary_projection),
        "rescue_history_context": {}
        if blockers
        else _context_summary(derived_memory_views, "rescue_history_summary"),
        "adherence_context": {}
        if blockers
        else _context_summary(derived_memory_views, "adherence_summary"),
        "history_review_notes": []
        if blockers
        else _history_review_notes(derived_memory_views),
        "missing_runtime_dependencies": [
            "CurrentBudgetView",
            "ActiveBodyPlanView",
            "OpenProposalsView",
            "human_or_runtime_trigger_source",
        ],
        "rescue_needed": None,
        "send_or_skip": None,
        "candidate_copy": None,
        "proposal_card": None,
        "primary_actions": [],
        "recommended_days": None,
        "daily_kcal_adjustment": None,
        "non_claims": list(NON_CLAIMS),
        **_non_runtime_flags(),
    }


def _memory_signal_summary(memory_summary_projection: Mapping[str, Any]) -> dict[str, int]:
    profile = _mapping(memory_summary_projection.get("preference_profile_summary"))
    suppression = _mapping(memory_summary_projection.get("suppression_summary"))
    return {
        "preference_candidate_count": len(
            list(profile.get("accepted_shadow_candidate_ids") or [])
        ),
        "negative_preference_blocker_count": len(
            list(profile.get("negative_preference_blockers") or [])
        ),
        "suppression_blocker_count": len(
            list(suppression.get("suppression_blockers") or [])
        ),
    }


def _suppression_context(
    memory_summary_projection: Mapping[str, Any],
) -> list[dict[str, Any]]:
    suppression = _mapping(memory_summary_projection.get("suppression_summary"))
    rows: list[dict[str, Any]] = []
    for row in suppression.get("suppression_blockers") or []:
        if not isinstance(row, Mapping):
            continue
        rows.append(
            {
                "candidate_id": str(row.get("candidate_id") or ""),
                "trigger_type": str(row.get("trigger_type") or "unknown"),
                "summary": str(row.get("summary") or ""),
                "review_context_only": True,
            }
        )
    return rows


def _context_summary(
    derived_memory_views: Mapping[str, Any],
    key: str,
) -> dict[str, Any]:
    context = _mapping(derived_memory_views.get(key))
    if context.get("is_durable_memory_truth") is not False:
        return {}
    return dict(context)


def _history_review_notes(derived_memory_views: Mapping[str, Any]) -> list[str]:
    notes: list[str] = []
    if _context_summary(derived_memory_views, "rescue_history_summary"):
        notes.append("rescue_history_present_for_future_viability_review")
    if _context_summary(derived_memory_views, "adherence_summary"):
        notes.append("adherence_summary_present_for_future_viability_review")
    return notes


def _non_runtime_flags() -> dict[str, Any]:
    flags = dict(RESCUE_SHADOW_NON_RUNTIME_FLAGS)
    flags["runtime_effect_allowed"] = False
    return flags


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_shadow_summary_context_projection",
]
