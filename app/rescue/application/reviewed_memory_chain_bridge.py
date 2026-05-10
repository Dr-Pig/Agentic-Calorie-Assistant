from __future__ import annotations

from typing import Any, Mapping

from app.rescue.application.shadow_chain_runner import run_rescue_shadow_chain
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.reviewed_memory_chain_bridge"
)


def build_rescue_reviewed_memory_chain_contexts(
    *,
    memory_summary_projection: Mapping[str, Any],
    derived_memory_views: Mapping[str, Any],
    current_budget_view: Mapping[str, Any],
    active_body_plan_view: Mapping[str, Any],
) -> dict[str, Any]:
    overshoot = _int(current_budget_view.get("meal_consumption_total_kcal")) - _int(
        current_budget_view.get("effective_budget_kcal")
    )
    target_days = active_body_plan_view.get("target_days")
    rescue_history = _mapping(derived_memory_views.get("rescue_history_summary"))
    suppression = _mapping(memory_summary_projection.get("suppression_summary"))
    return {
        "budget_context": {
            "current_date": "shadow_lab",
            "overshoot_kcal": max(overshoot, 0),
            "remaining_budget_kcal": -max(overshoot, 0),
        },
        "body_plan_context": {
            "safety_floor_kcal": _int(active_body_plan_view.get("safety_floor_kcal")),
            "target_days_count": len(target_days) if isinstance(target_days, list) else 0,
            "sex": str(active_body_plan_view.get("sex") or "unspecified"),
        },
        "rescue_history_context": {
            "recent_rescue_count": _int(rescue_history.get("rescue_event_count")),
            "summary": str(rescue_history.get("summary") or ""),
            "rescue_viability_posture": str(
                rescue_history.get("rescue_viability_posture") or "unknown"
            ),
        },
        "suppression_context": [
            {
                "trigger_type": str(item.get("trigger_type") or "unknown"),
                "summary": str(item.get("summary") or ""),
            }
            for item in _items(suppression.get("suppression_blockers"))
        ],
        "runtime_effect_allowed": False,
        "manager_context_injected": False,
        "proposal_committed": False,
        "rescue_committed": False,
    }


def run_rescue_reviewed_memory_shadow_chain(
    *,
    memory_summary_projection: Mapping[str, Any],
    derived_memory_views: Mapping[str, Any],
    current_budget_view: Mapping[str, Any],
    active_body_plan_view: Mapping[str, Any],
    open_proposals_view: Mapping[str, Any],
    proposal_candidate_output: Mapping[str, Any],
) -> dict[str, Any]:
    contexts = build_rescue_reviewed_memory_chain_contexts(
        memory_summary_projection=memory_summary_projection,
        derived_memory_views=derived_memory_views,
        current_budget_view=current_budget_view,
        active_body_plan_view=active_body_plan_view,
    )
    artifact = run_rescue_shadow_chain(
        memory_summary_projection=memory_summary_projection,
        derived_memory_views=derived_memory_views,
        current_budget_view=current_budget_view,
        active_body_plan_view=active_body_plan_view,
        open_proposals_view=open_proposals_view,
        proposal_candidate_output=proposal_candidate_output,
        budget_context=contexts["budget_context"],
        body_plan_context=contexts["body_plan_context"],
        rescue_history_context=contexts["rescue_history_context"],
        suppression_context=contexts["suppression_context"],
    )
    artifact["reviewed_memory_bridge_used"] = artifact.get("status") == "pass"
    artifact["source_memory_artifact_type"] = memory_summary_projection.get("artifact_type")
    artifact["runtime_effect_allowed"] = False
    artifact["manager_context_injected"] = False
    artifact["proposal_committed"] = False
    return artifact


def _items(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_reviewed_memory_chain_contexts",
    "run_rescue_reviewed_memory_shadow_chain",
]
