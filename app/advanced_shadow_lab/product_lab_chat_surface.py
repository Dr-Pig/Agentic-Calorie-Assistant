from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
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
        "surface": "chat",
        "copy": _copy(packet, workflow_family),
        "memory_context_refs": [
            str(item) for item in packet.get("memory_context_refs") or []
        ],
        "memory_context_applied": packet.get("memory_context_applied") is True,
        "product_runtime_output_refs": [
            str(item) for item in packet.get("product_runtime_output_refs") or []
        ],
        "recommendation_offer": _recommendation_offer(packet),
        "rescue_proposal": _rescue_proposal(packet),
        "pending_intake_draft_ids": [
            str(item) for item in packet.get("pending_intake_draft_ids") or []
        ],
        "controls_visible": True,
        "actions": [
            _action(session_id, turn_id, candidate_id, "dismiss"),
            _action(session_id, turn_id, candidate_id, "snooze"),
            _action(session_id, turn_id, candidate_id, "undo"),
        ],
        "served_to_lab_user": True,
        "served_to_mainline_user": False,
        "delivery_attempted_outside_lab": False,
        "scheduler_enqueued": False,
        "canonical_mutation_requested": False,
    }


def _action(
    session_id: str,
    turn_id: str,
    candidate_id: str,
    action: str,
) -> dict[str, str]:
    return {
        "action_id": f"{session_id}:{turn_id}:{candidate_id}:{action}",
        "action": action,
        "scope": "candidate_instance",
    }


def _copy(packet: Mapping[str, Any], workflow_family: str) -> str:
    product_copy = str(packet.get("product_lab_copy") or "").strip()
    if product_copy:
        return product_copy
    preview = str(packet.get("lab_only_copy_preview") or "").strip()
    if preview:
        return preview
    if workflow_family == "recommendation":
        return "I can help pick a stable option for this moment."
    if workflow_family == "rescue":
        return "I can help adjust the next step without making it harsh."
    return "I can help with this when it is useful."


def _recommendation_offer(packet: Mapping[str, Any]) -> dict[str, Any]:
    ux = packet.get("recommendation_ux_packet")
    if not isinstance(ux, Mapping):
        return {}
    handoff = _mapping(packet.get("pending_intake_handoff_packet"))
    return {
        "primary_candidate_id": str(ux.get("primary_candidate_id") or ""),
        "backup_candidate_ids": [str(item) for item in ux.get("backup_candidate_ids") or []],
        "candidate_snapshot": dict(_mapping(handoff.get("candidate_snapshot"))),
        "offer_actions": [dict(item) for item in ux.get("actions") or [] if isinstance(item, Mapping)],
        "intake_handoff_state": str(handoff.get("handoff_state") or ""),
        "canonical_commit_requested": handoff.get("canonical_commit_requested") is True,
        "requires_explicit_user_intake_action": any(
            item.get("requires_explicit_user_intake_action") is True
            for item in ux.get("actions") or []
            if isinstance(item, Mapping)
        ),
        "source_pending_intake_handoff_artifact_type": str(
            handoff.get("artifact_type") or ""
        ),
    }


def _rescue_proposal(packet: Mapping[str, Any]) -> dict[str, Any]:
    proposal = _mapping(packet.get("rescue_proposal_packet"))
    if not proposal:
        return {}
    pending = _mapping(proposal.get("pending_rescue_commit_packet"))
    return {
        "handoff_state": str(pending.get("handoff_state") or ""),
        "primary_actions": [str(item) for item in proposal.get("primary_actions") or []],
        "proposal_card": dict(_mapping(proposal.get("proposal_card"))),
        "guardrail_math": dict(_mapping(proposal.get("guardrail_math"))),
        "canonical_commit_requested": pending.get("canonical_commit_requested") is True,
        "proposal_committed": pending.get("proposal_committed") is True,
        "source_pending_rescue_commit_artifact_type": str(
            pending.get("artifact_type") or ""
        ),
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
