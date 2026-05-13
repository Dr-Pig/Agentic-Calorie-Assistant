from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.recommendation_posture_handoff"
)


def build_rescue_recommendation_posture_handoff(
    *,
    recommendation_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    if not recommendation_artifact:
        return _artifact(status="omitted", reason="recommendation_not_run")
    served = recommendation_artifact.get("recommendation_served_to_lab") is True
    if not served:
        return _artifact(status="omitted", reason="recommendation_not_served")
    primary = _mapping(_mapping(recommendation_artifact.get("offer_synthesis")).get("selected_primary"))
    pending = _mapping(recommendation_artifact.get("pending_intake_handoff_packet"))
    blockers = _blockers(primary=primary, pending=pending)
    return _artifact(
        status="blocked" if blockers else "pass",
        blockers=blockers,
        selected_candidate_id=str(primary.get("candidate_id") or ""),
        estimated_kcal_range=dict(_mapping(primary.get("estimated_kcal_range"))),
        pending_intake_confirmation_required=(
            pending.get("requires_user_confirmation_before_commit") is True
        ),
        source_refs=[
            str(ref) for ref in primary.get("source_refs") or [] if str(ref)
        ],
        source_recommendation_artifact_type=str(
            recommendation_artifact.get("artifact_type") or ""
        ),
    )


def _artifact(
    *,
    status: str,
    reason: str = "",
    blockers: list[str] | None = None,
    selected_candidate_id: str = "",
    estimated_kcal_range: dict[str, Any] | None = None,
    pending_intake_confirmation_required: bool = False,
    source_refs: list[str] | None = None,
    source_recommendation_artifact_type: str = "",
) -> dict[str, Any]:
    return {
        "artifact_type": "rescue_recommendation_posture_handoff",
        "status": status,
        "reason": reason,
        "owner": "app/rescue",
        "consumer": "rescue_budget_and_negotiation_context",
        "recommendation_offer_served_to_lab": status == "pass",
        "selected_recommendation_candidate_id": selected_candidate_id,
        "estimated_kcal_range": estimated_kcal_range or {},
        "pending_intake_confirmation_required": pending_intake_confirmation_required,
        "offer_is_proposal_only": status == "pass",
        "must_not_count_offer_as_consumed": status == "pass",
        "source_refs": source_refs or [],
        "source_recommendation_artifact_type": source_recommendation_artifact_type,
        "meal_thread_mutated": False,
        "ledger_entry_created": False,
        "rescue_budget_view_mutated": False,
        "canonical_product_mutation_allowed": False,
        "blockers": blockers or [],
    }


def _blockers(*, primary: Mapping[str, Any], pending: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not primary.get("candidate_id"):
        blockers.append("recommendation_artifact.selected_primary_missing")
    if pending.get("requires_user_confirmation_before_commit") is not True:
        blockers.append("pending_intake_handoff.confirmation_required_missing")
    if pending.get("canonical_commit_requested") is True:
        blockers.append("pending_intake_handoff.canonical_commit_requested")
    return blockers


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_recommendation_posture_handoff",
]
