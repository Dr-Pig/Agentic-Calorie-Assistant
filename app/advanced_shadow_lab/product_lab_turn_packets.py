from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_pending_intake_surface import (
    pending_intake_chat_packets,
)


def lab_chat_response_packet(
    chain: Mapping[str, Any],
    control_state: Mapping[str, Any],
    *,
    memory_context_pack: Mapping[str, Any] | None = None,
    product_recommendation: Mapping[str, Any] | None = None,
    product_rescue: Mapping[str, Any] | None = None,
    product_proactive: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    packet = chain.get("chat_ux_packet")
    if not isinstance(packet, Mapping):
        return {
            "artifact_type": "advanced_product_lab_chat_response_packet",
            "status": "blocked",
            "packet_count": 0,
            "served_to_lab_surface": False,
            "served_to_mainline_user": False,
            "blockers": ["chat_ux_packet.missing"],
        }
    memory_pack = dict(memory_context_pack or {})
    selected_record_ids = [
        str(item) for item in memory_pack.get("selected_record_ids") or []
    ]
    chat_packets = _packets_with_memory_refs(
        _packets_allowed_by_proactive(
            [
                *list(packet.get("chat_packets") or []),
                *pending_intake_chat_packets(product_proactive=product_proactive or {}),
            ],
            product_proactive or {},
        ),
        selected_record_ids,
        product_recommendation=product_recommendation or {},
        product_rescue=product_rescue or {},
        product_proactive=product_proactive or {},
    )
    candidate_states = list(control_state.get("candidate_states") or [])
    return {
        "artifact_type": "advanced_product_lab_chat_response_packet",
        "status": str(packet.get("status") or "blocked"),
        "packet_count": int(packet.get("packet_count") or 0),
        "packet_mode": "lab_served_product_chat_packet",
        "surface": "chat",
        "chat_first": True,
        "source_artifact_type": str(packet.get("artifact_type") or ""),
        "source_packet_mode": str(packet.get("packet_mode") or ""),
        "served_to_lab_surface": packet.get("status") == "pass",
        "served_to_mainline_user": False,
        "delivery_attempted_outside_lab": False,
        "scheduler_enqueued": False,
        "canonical_mutation_requested": False,
        "candidate_states": candidate_states,
        "visible_chat_packets": visible_chat_packets(chat_packets, candidate_states),
        "memory_context_applied": bool(selected_record_ids),
        "memory_context_refs": selected_record_ids,
        "memory_context_source_artifact_type": memory_pack.get("artifact_type"),
        "product_outputs_applied": any(
            bool(_mapping(artifact))
            for artifact in (product_recommendation, product_rescue, product_proactive)
        ),
        "lab_runtime_capabilities": {
            "memory_tools_enabled": memory_pack.get("memory_tools_enabled") is True,
            "memory_context_injected": memory_pack.get("memory_context_injected") is True,
            "recommendation_served_to_lab": packet.get("status") == "pass",
            "rescue_served_to_lab": packet.get("status") == "pass",
            "proactive_chat_packet_served_to_lab": packet.get("status") == "pass",
            "mainline_activation_enabled": False,
        },
        "blockers": list(packet.get("blockers") or []),
        "chat_packets": chat_packets,
    }


def chat_packet_blockers(packet: Mapping[str, Any]) -> list[str]:
    if packet.get("status") == "pass":
        return []
    return [f"lab_chat_response_packet.{blocker}" for blocker in packet.get("blockers") or []]


def chat_packets(chain: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    packet = chain.get("chat_ux_packet")
    if not isinstance(packet, Mapping):
        return []
    return [item for item in packet.get("chat_packets") or [] if isinstance(item, Mapping)]


def visible_chat_packets(
    packets: list[Mapping[str, Any]],
    candidate_states: list[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    visibility = {
        str(state.get("candidate_id") or ""): state.get("visible_in_lab") is True
        for state in candidate_states
    }
    return [
        packet
        for packet in packets
        if visibility.get(str(packet.get("packet_id") or ""), True) is True
    ]


def _packets_with_memory_refs(
    packets: list[Mapping[str, Any]],
    selected_record_ids: list[str],
    *,
    product_recommendation: Mapping[str, Any],
    product_rescue: Mapping[str, Any],
    product_proactive: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            **dict(packet),
            "memory_context_refs": list(selected_record_ids),
            "memory_context_applied": bool(selected_record_ids),
            **_product_fields(
                packet,
                product_recommendation=product_recommendation,
                product_rescue=product_rescue,
                product_proactive=product_proactive,
            ),
        }
        for packet in packets
    ]


def _packets_allowed_by_proactive(
    packets: list[Mapping[str, Any]],
    product_proactive: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    if product_proactive.get("artifact_type") != "advanced_product_lab_proactive_runtime_artifact":
        return packets
    allowed = {
        str(candidate.get("trigger_type") or "")
        for candidate in product_proactive.get("candidates") or []
        if isinstance(candidate, Mapping)
    }
    return [
        packet
        for packet in packets
        if str(packet.get("trigger_type") or "") in allowed
        or str(packet.get("workflow_family") or "") == "general_chat"
    ]


def _product_fields(
    packet: Mapping[str, Any],
    *,
    product_recommendation: Mapping[str, Any],
    product_rescue: Mapping[str, Any],
    product_proactive: Mapping[str, Any],
) -> dict[str, Any]:
    family = str(packet.get("workflow_family") or "")
    if family == "recommendation":
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
    if family == "rescue":
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
    return {"product_lab_copy": "", "product_runtime_output_refs": []}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
