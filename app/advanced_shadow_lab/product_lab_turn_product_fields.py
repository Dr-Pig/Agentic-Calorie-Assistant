from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_calibration_packets import calibration_product_fields
from app.advanced_shadow_lab.product_lab_no_plan_packets import no_plan_product_fields
from app.advanced_shadow_lab.product_lab_planned_event_packets import planned_event_product_fields
from app.advanced_shadow_lab.product_lab_swap_packets import swap_product_fields


def product_fields(
    packet: Mapping[str, Any],
    *,
    product_recommendation: Mapping[str, Any],
    product_rescue: Mapping[str, Any],
    product_proactive: Mapping[str, Any],
) -> dict[str, Any]:
    family = str(packet.get("workflow_family") or "")
    no_plan_fields = no_plan_product_fields(packet)
    if no_plan_fields:
        return no_plan_fields
    swap_fields = swap_product_fields(packet)
    if swap_fields:
        return swap_fields
    calibration_fields = calibration_product_fields(packet)
    if calibration_fields:
        return calibration_fields
    planned_fields = planned_event_product_fields(packet)
    if planned_fields:
        return planned_fields
    if family == "recommendation":
        return _recommendation_fields(product_recommendation, product_proactive)
    if family == "rescue":
        return _rescue_fields(product_rescue, product_proactive)
    return {"product_lab_copy": "", "product_runtime_output_refs": []}


def _recommendation_fields(
    product_recommendation: Mapping[str, Any],
    product_proactive: Mapping[str, Any],
) -> dict[str, Any]:
    ux = _mapping(_mapping(product_recommendation.get("offer_synthesis")).get("ux_packet"))
    return {
        "product_lab_copy": str(ux.get("explanation") or ""),
        "recommendation_ux_packet": dict(ux),
        "pending_intake_handoff_packet": dict(
            product_recommendation.get("pending_intake_handoff_packet") or {}
        ),
        "product_runtime_output_refs": [
            str(product_recommendation.get("artifact_type") or ""),
            str(product_proactive.get("artifact_type") or ""),
        ],
    }


def _rescue_fields(
    product_rescue: Mapping[str, Any],
    product_proactive: Mapping[str, Any],
) -> dict[str, Any]:
    card = _mapping(product_rescue.get("proposal_card"))
    copy = " ".join(
        item for item in [str(card.get("headline") or ""), str(card.get("summary") or "")] if item
    )
    return {
        "product_lab_copy": copy,
        "rescue_proposal_packet": {
            "proposal_card": dict(card),
            "primary_actions": list(product_rescue.get("primary_actions") or []),
            "negotiation_affordances": list(product_rescue.get("negotiation_affordances") or []),
            "guardrail_math": dict(product_rescue.get("guardrail_math") or {}),
            "pending_rescue_commit_packet": dict(
                product_rescue.get("pending_rescue_commit_packet") or {}
            ),
        },
        "product_runtime_output_refs": [
            str(product_rescue.get("artifact_type") or ""),
            str(product_proactive.get("artifact_type") or ""),
        ],
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["product_fields"]
