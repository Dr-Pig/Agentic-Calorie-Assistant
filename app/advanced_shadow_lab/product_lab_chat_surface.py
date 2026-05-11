from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_chat_surface_fields import (
    chat_copy,
    message_actions,
    product_surface_fields,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_chat_surface"
)

NON_CLAIMS = [
    "not_frontend_route",
    "not_self_use_v1_chat_surface",
    "not_production_notification",
    "not_scheduler_delivery",
    "not_canonical_mutation",
]


def build_advanced_product_lab_chat_surface(
    *,
    session_id: str,
    turn_id: str,
    lab_chat_response_packet: Mapping[str, Any],
) -> dict[str, Any]:
    visible_packets = _visible_packets(lab_chat_response_packet)
    blockers = _packet_blockers(lab_chat_response_packet)
    messages = [] if blockers else [
        _message(session_id=session_id, turn_id=turn_id, packet=packet)
        for packet in visible_packets
    ]
    return {
        "artifact_type": "advanced_product_lab_chat_surface_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/advanced_shadow_lab/product_lab_chat_surface.py",
        "consumer": "advanced_product_lab_fixture_live_and_e2e_tests",
        "retirement_trigger": "approved_advanced_product_lab_surface_activation_plan",
        "surface": "chat",
        "surface_mode": "lab_served_chat",
        "chat_first": True,
        "served_to_lab_user": not bool(blockers),
        "served_to_mainline_user": False,
        "visible_message_count": len(messages),
        "messages": messages,
        "blockers": blockers,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _packet_blockers(packet: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if packet.get("artifact_type") != "advanced_product_lab_chat_response_packet":
        blockers.append("lab_chat_response_packet.unsupported_artifact_type")
    if packet.get("status") != "pass":
        blockers.append(f"lab_chat_response_packet.status_{packet.get('status') or 'missing'}")
    if packet.get("served_to_mainline_user") is True:
        blockers.append("lab_chat_response_packet.served_to_mainline_user")
    if packet.get("scheduler_enqueued") is True:
        blockers.append("lab_chat_response_packet.scheduler_enqueued")
    if packet.get("canonical_mutation_requested") is True:
        blockers.append("lab_chat_response_packet.canonical_mutation_requested")
    return blockers


def _message(
    *,
    session_id: str,
    turn_id: str,
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_id = str(packet.get("packet_id") or "")
    workflow_family = str(packet.get("workflow_family") or "general_chat")
    return {
        "message_id": f"{session_id}:{turn_id}:{candidate_id}",
        "candidate_id": candidate_id,
        "workflow_family": workflow_family,
        "trigger_type": str(packet.get("trigger_type") or ""),
        "surface": "chat",
        "copy": chat_copy(packet, workflow_family),
        "memory_context_refs": [
            str(item) for item in packet.get("memory_context_refs") or []
        ],
        "memory_context_applied": packet.get("memory_context_applied") is True,
        "product_runtime_output_refs": [
            str(item) for item in packet.get("product_runtime_output_refs") or []
        ],
        **product_surface_fields(packet),
        "pending_intake_draft_ids": [
            str(item) for item in packet.get("pending_intake_draft_ids") or []
        ],
        "controls_visible": True,
        "actions": message_actions(
            session_id=session_id,
            turn_id=turn_id,
            candidate_id=candidate_id,
            packet=packet,
        ),
        "served_to_lab_user": True,
        "served_to_mainline_user": False,
        "delivery_attempted_outside_lab": False,
        "scheduler_enqueued": False,
        "canonical_mutation_requested": False,
    }


def _visible_packets(packet: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        item
        for item in packet.get("visible_chat_packets") or []
        if isinstance(item, Mapping)
    ]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_advanced_product_lab_chat_surface",
]
