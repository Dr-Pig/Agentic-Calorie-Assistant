from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.three_node_shadow_policy import candidate_guard
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.rescue_posture_handoff"
)
COMMIT_ARTIFACT = "isolated_lab_rescue_commit_effect"
PRODUCTION_DORMANT_FLAGS = {
    "mainline_activation_enabled": False,
    "mainline_route_or_api_mount_allowed": False,
    "production_scheduler_delivery_allowed": False,
    "production_db_mutation_allowed": False,
    "canonical_mutation_changed": False,
    "durable_product_memory_written_in_mainline": False,
    "recommendation_served": False,
    "recommendation_intent_state_created": False,
    "intake_handoff_created": False,
}


def build_recommendation_rescue_posture_handoff(
    *,
    isolated_lab_rescue_commit_effect: Mapping[str, Any],
    recommendation_payload: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = _blockers(isolated_lab_rescue_commit_effect)
    if blockers:
        return _artifact(status="blocked", blockers=blockers)
    refreshed = _mapping(
        isolated_lab_rescue_commit_effect.get("refreshed_current_budget_view")
    )
    commit = _mapping(isolated_lab_rescue_commit_effect.get("rescue_commit_effect"))
    patched_payload = _patched_payload(
        recommendation_payload=recommendation_payload,
        refreshed_current_budget_view=refreshed,
        commit_effect=commit,
    )
    return _artifact(
        status="pass",
        recommendation_runtime_patch=patched_payload,
        rescue_posture_summary=_rescue_posture_summary(commit, refreshed),
        candidate_guard_preview=candidate_guard(patched_payload),
    )


def _artifact(
    *,
    status: str,
    blockers: list[str] | None = None,
    recommendation_runtime_patch: dict[str, Any] | None = None,
    rescue_posture_summary: dict[str, Any] | None = None,
    candidate_guard_preview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "recommendation_rescue_posture_handoff",
        "status": status,
        "owner": "app/recommendation",
        "consumer": "recommendation_planning_and_candidate_guard",
        "lab_enabled": True,
        "lab_isolated": True,
        "handoff_scope": "short_term_caloric_posture_only",
        "recommendation_runtime_patch": recommendation_runtime_patch,
        "rescue_posture_summary": rescue_posture_summary,
        "candidate_guard_preview": candidate_guard_preview,
        "blockers": blockers or [],
        **dict(PRODUCTION_DORMANT_FLAGS),
    }


def _blockers(commit_effect: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if commit_effect.get("artifact_type") != COMMIT_ARTIFACT:
        blockers.append("rescue_commit_effect.unsupported_artifact_type")
    if commit_effect.get("status") != "pass":
        blockers.append("rescue_commit_effect.status_not_pass")
    if not _mapping(commit_effect.get("refreshed_current_budget_view")):
        blockers.append("rescue_commit_effect.refreshed_current_budget_view_missing")
    if not _mapping(commit_effect.get("rescue_commit_effect")):
        blockers.append("rescue_commit_effect.commit_effect_missing")
    return blockers


def _patched_payload(
    *,
    recommendation_payload: Mapping[str, Any],
    refreshed_current_budget_view: Mapping[str, Any],
    commit_effect: Mapping[str, Any],
) -> dict[str, Any]:
    patched = dict(recommendation_payload)
    patched["current_budget_view"] = dict(refreshed_current_budget_view)
    existing_rescue_context = _mapping(recommendation_payload.get("open_rescue_context"))
    patched["open_rescue_context"] = {
        **dict(existing_rescue_context),
        "accepted_rescue_overlay_active": True,
        "proposal_id": str(commit_effect.get("proposal_id") or ""),
        "daily_kcal_adjustment": _int(commit_effect.get("daily_kcal_adjustment")),
        "recommended_days": _int(commit_effect.get("recommended_days")),
        "effective_from": str(commit_effect.get("effective_from") or ""),
        "effective_to": str(commit_effect.get("effective_to") or ""),
        "remaining_budget_kcal_after_overlay": _int(
            refreshed_current_budget_view.get("remaining_kcal")
        ),
    }
    return patched


def _rescue_posture_summary(
    commit_effect: Mapping[str, Any],
    refreshed_current_budget_view: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "accepted_rescue_overlay_active": True,
        "proposal_id": str(commit_effect.get("proposal_id") or ""),
        "daily_kcal_adjustment": _int(commit_effect.get("daily_kcal_adjustment")),
        "recommended_days": _int(commit_effect.get("recommended_days")),
        "remaining_budget_kcal_after_overlay": _int(
            refreshed_current_budget_view.get("remaining_kcal")
        ),
        "recommendation_intent_state_created": False,
        "recommendation_offer_served": False,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return int(value or 0)


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_recommendation_rescue_posture_handoff"]
