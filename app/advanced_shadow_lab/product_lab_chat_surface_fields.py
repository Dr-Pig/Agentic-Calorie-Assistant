from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_chat_surface_calibration import (
    calibration_proposal,
)
from app.advanced_shadow_lab.product_lab_chat_surface_no_plan import no_plan_degraded


def chat_copy(packet: Mapping[str, Any], workflow_family: str) -> str:
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


def message_actions(
    *,
    session_id: str,
    turn_id: str,
    candidate_id: str,
    packet: Mapping[str, Any],
) -> list[dict[str, str]]:
    actions = [
        _action(session_id, turn_id, candidate_id, "dismiss"),
        _action(session_id, turn_id, candidate_id, "snooze"),
        _action(session_id, turn_id, candidate_id, "undo"),
    ]
    if packet.get("memory_action_allowed") is True:
        actions.append(_action(session_id, turn_id, candidate_id, "remember_memory"))
    return actions


def recommendation_offer(packet: Mapping[str, Any]) -> dict[str, Any]:
    ux = packet.get("recommendation_ux_packet")
    if not isinstance(ux, Mapping):
        return {}
    handoff = _mapping(packet.get("pending_intake_handoff_packet"))
    return {
        "primary_candidate_id": str(ux.get("primary_candidate_id") or ""),
        "backup_candidate_ids": [str(item) for item in ux.get("backup_candidate_ids") or []],
        "candidate_snapshot": dict(_mapping(handoff.get("candidate_snapshot"))),
        "pre_meal_planning": dict(_mapping(ux.get("pre_meal_planning_packet"))),
        "swap_suggestion": dict(_mapping(ux.get("swap_suggestion_packet"))),
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


def rescue_proposal(packet: Mapping[str, Any]) -> dict[str, Any]:
    proposal = _mapping(packet.get("rescue_proposal_packet"))
    if not proposal:
        return {}
    pending = _mapping(proposal.get("pending_rescue_commit_packet"))
    return {
        "handoff_state": str(pending.get("handoff_state") or ""),
        "primary_actions": [str(item) for item in proposal.get("primary_actions") or []],
        "negotiation_affordances": [
            str(item) for item in proposal.get("negotiation_affordances") or []
        ],
        "proposal_card": dict(_mapping(proposal.get("proposal_card"))),
        "guardrail_math": dict(_mapping(proposal.get("guardrail_math"))),
        "canonical_commit_requested": pending.get("canonical_commit_requested") is True,
        "proposal_committed": pending.get("proposal_committed") is True,
        "source_pending_rescue_commit_artifact_type": str(
            pending.get("artifact_type") or ""
        ),
    }


def swap_suggestion(packet: Mapping[str, Any]) -> dict[str, Any]:
    return dict(_mapping(packet.get("swap_suggestion_packet")))


def product_surface_fields(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "recommendation_offer": recommendation_offer(packet),
        "rescue_proposal": rescue_proposal(packet),
        "swap_suggestion": swap_suggestion(packet),
        "calibration_proposal": calibration_proposal(packet),
        "no_plan_degraded": no_plan_degraded(packet),
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


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "chat_copy",
    "message_actions",
    "product_surface_fields",
]
