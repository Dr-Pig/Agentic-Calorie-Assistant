from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_no_plan_packets"
)


def with_no_plan_degraded_chat_packets(
    packets: list[Mapping[str, Any]],
    no_plan: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    if no_plan.get("status") != "pass":
        return list(packets)
    return [_intake_packet(no_plan), _budget_query_packet(no_plan)]


def no_plan_product_fields(packet: Mapping[str, Any]) -> dict[str, Any]:
    data = _mapping(packet.get("no_plan_degraded_packet"))
    if not data:
        return {}
    return {
        "product_lab_copy": str(packet.get("product_lab_copy") or ""),
        "no_plan_degraded_packet": dict(data),
        "product_runtime_output_refs": [
            str(item) for item in packet.get("product_runtime_output_refs") or []
        ],
    }


def _intake_packet(artifact: Mapping[str, Any]) -> dict[str, Any]:
    intake = _mapping(artifact.get("intake_packet"))
    kcal = int(intake.get("estimated_kcal") or 0)
    return {
        "packet_id": "no_plan_intake_logging:0",
        "workflow_family": "intake_logging",
        "trigger_type": "no_plan_intake_logging",
        "product_lab_copy": f"Estimated {kcal} kcal for {intake.get('meal_title')}.",
        "no_plan_degraded_packet": {
            "intake_packet": dict(intake),
            "today_ui_mirror": dict(_mapping(artifact.get("today_ui_mirror"))),
        },
        "product_runtime_output_refs": [str(artifact.get("artifact_type") or "")],
    }


def _budget_query_packet(artifact: Mapping[str, Any]) -> dict[str, Any]:
    budget = _mapping(artifact.get("budget_query_packet"))
    return {
        "packet_id": "no_plan_budget_query:0",
        "workflow_family": "budget_query",
        "trigger_type": "no_plan_budget_query",
        "product_lab_copy": "No target is set yet, so remaining budget stays unavailable.",
        "no_plan_degraded_packet": {
            "budget_query_packet": dict(budget),
            "today_ui_mirror": dict(_mapping(artifact.get("today_ui_mirror"))),
        },
        "product_runtime_output_refs": [str(artifact.get("artifact_type") or "")],
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "no_plan_product_fields",
    "with_no_plan_degraded_chat_packets",
]
