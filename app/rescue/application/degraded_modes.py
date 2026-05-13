from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.degraded_modes"
)
CONSERVATIVE_SAFETY_FLOOR_KCAL = 1500


def build_rescue_degraded_mode_result(
    *,
    read_model_input_packet: Mapping[str, Any],
    onboarding_status: Mapping[str, Any],
    provider_status: Mapping[str, Any],
) -> dict[str, Any]:
    views = _views(read_model_input_packet)
    if not views["current_budget"].get("view_available"):
        return _result(
            status="blocked",
            degraded_mode="required_view_unavailable",
            rescue_flow_allowed=False,
            rescue_skipped="budget_view_unavailable",
            recommended_next_step="show_budget_unavailable",
        )
    if (
        not views["active_body_plan"].get("view_available")
        and onboarding_status.get("body_plan_complete") is False
    ):
        return _result(
            status="blocked",
            degraded_mode="onboarding_missing",
            rescue_flow_allowed=False,
            proactive_budget_alert_allowed=False,
            recommended_next_step="route_to_onboarding",
        )
    if not views["active_body_plan"].get("view_available"):
        return _result(
            status="pass",
            degraded_mode="conservative_body_plan_fallback",
            rescue_flow_allowed=True,
            safety_floor_source="conservative_fallback",
            conservative_safety_floor_kcal=CONSERVATIVE_SAFETY_FLOOR_KCAL,
        )
    if not views["open_proposals"].get("view_available"):
        return _result(
            status="pass",
            degraded_mode="open_proposals_view_unavailable",
            rescue_flow_allowed=True,
            trace_notes=["open_proposal_duplicate_risk"],
        )
    if provider_status.get("proposal_shaping_available") is False:
        return _result(
            status="pass",
            degraded_mode="provider_unavailable_logging_first",
            rescue_flow_allowed=True,
            proposal_shaping_allowed=False,
            response_template_allowed=True,
            provider_recomputed_math=False,
            recommended_next_step="deterministic_template_only",
        )
    return _result(
        status="pass",
        degraded_mode="none",
        rescue_flow_allowed=True,
    )


def _result(
    *,
    status: str,
    degraded_mode: str,
    rescue_flow_allowed: bool,
    rescue_skipped: str | None = None,
    proactive_budget_alert_allowed: bool = True,
    proposal_shaping_allowed: bool = True,
    response_template_allowed: bool = False,
    provider_recomputed_math: bool = False,
    recommended_next_step: str = "continue_rescue_flow",
    safety_floor_source: str = "active_body_plan",
    conservative_safety_floor_kcal: int | None = None,
    trace_notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "rescue_degraded_mode_result",
        "status": status,
        "owner": "app/rescue",
        "consumer": "rescue_phase1_runtime_lab_nodes",
        "decision_mode": "deterministic",
        "degraded_mode": degraded_mode,
        "rescue_flow_allowed": rescue_flow_allowed,
        "rescue_skipped": rescue_skipped,
        "recommended_next_step": recommended_next_step,
        "safety_floor_source": safety_floor_source,
        "conservative_safety_floor_kcal": conservative_safety_floor_kcal,
        "proposal_shaping_allowed": proposal_shaping_allowed,
        "response_template_allowed": response_template_allowed,
        "provider_recomputed_math": provider_recomputed_math,
        "proactive_budget_alert_allowed": proactive_budget_alert_allowed,
        "trace_notes": trace_notes or [],
        "proposal_card": None,
        "ledger_entry_created": False,
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "production_scheduler_delivery_allowed": False,
        "manager_context_packet_changed_in_mainline": False,
        "durable_product_memory_written_in_mainline": False,
    }


def _views(packet: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        "current_budget": _mapping(packet.get("current_budget_view")),
        "active_body_plan": _mapping(packet.get("active_body_plan_view")),
        "open_proposals": _mapping(packet.get("open_proposals_view")),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "CONSERVATIVE_SAFETY_FLOOR_KCAL",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_degraded_mode_result",
]
