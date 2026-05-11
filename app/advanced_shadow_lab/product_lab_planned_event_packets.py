from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_planned_event_packets"
)


def with_planned_event_chat_packet(
    packets: list[Mapping[str, Any]],
    planned_event_rescue: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    if planned_event_rescue.get("status") != "pass":
        return list(packets)
    return [
        *[
            packet
            for packet in packets
            if str(packet.get("trigger_type") or "") != "rescue_nudge"
        ],
        _planned_event_packet(planned_event_rescue),
    ]


def with_planned_event_guidance_chat_packet(
    packets: list[Mapping[str, Any]],
    planned_event_guidance: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    if planned_event_guidance.get("status") != "pass":
        return list(packets)
    return [_planned_event_guidance_packet(planned_event_guidance)]


def planned_event_product_fields(packet: Mapping[str, Any]) -> dict[str, Any]:
    guidance_packet = _mapping(packet.get("planned_event_guidance_packet"))
    if guidance_packet:
        return {
            "product_lab_copy": str(packet.get("product_lab_copy") or ""),
            "planned_event_guidance_packet": dict(guidance_packet),
            "product_runtime_output_refs": [
                str(item) for item in packet.get("product_runtime_output_refs") or []
            ],
        }
    rescue_packet = _mapping(packet.get("rescue_proposal_packet"))
    if not rescue_packet:
        return {}
    return {
        "product_lab_copy": str(packet.get("product_lab_copy") or ""),
        "rescue_proposal_packet": dict(rescue_packet),
        "product_runtime_output_refs": [
            str(item) for item in packet.get("product_runtime_output_refs") or []
        ],
    }


def _planned_event_guidance_packet(artifact: Mapping[str, Any]) -> dict[str, Any]:
    card = _mapping(artifact.get("guidance_card"))
    return {
        "packet_id": "planned_event_guidance:0",
        "workflow_family": "rescue",
        "trigger_type": "planned_event_guidance",
        "product_lab_copy": (
            f"For {card.get('event_label')}, keep about "
            f"{card.get('suggested_reserve_kcal')} kcal open for dinner and "
            f"cap lunch around {card.get('lunch_cap_kcal')} kcal."
        ),
        "planned_event_guidance_packet": {
            "guidance_card": dict(card),
            "informational_only": True,
            "proposal_created": False,
            "canonical_product_mutation_allowed": False,
        },
        "product_runtime_output_refs": [str(artifact.get("artifact_type") or "")],
    }


def _planned_event_packet(artifact: Mapping[str, Any]) -> dict[str, Any]:
    card = _mapping(artifact.get("proposal_card"))
    return {
        "packet_id": "planned_event_rescue:0",
        "workflow_family": "rescue",
        "trigger_type": "planned_event_rescue",
        "product_lab_copy": " ".join(
            item
            for item in [str(card.get("headline") or ""), str(card.get("summary") or "")]
            if item
        ),
        "rescue_proposal_packet": {
            "proposal_card": dict(card),
            "primary_actions": list(artifact.get("primary_actions") or []),
            "negotiation_affordances": list(
                artifact.get("negotiation_affordances") or []
            ),
            "guardrail_math": dict(_mapping(artifact.get("guardrail_math"))),
            "pending_rescue_commit_packet": dict(
                _mapping(artifact.get("pending_rescue_commit_packet"))
            ),
        },
        "product_runtime_output_refs": [str(artifact.get("artifact_type") or "")],
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "planned_event_product_fields",
    "with_planned_event_chat_packet",
    "with_planned_event_guidance_chat_packet",
]
