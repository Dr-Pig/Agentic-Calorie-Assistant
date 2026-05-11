from __future__ import annotations

from typing import Any, Mapping


def active_row(turn_id: str, message: Mapping[str, Any]) -> dict[str, Any]:
    proposal = mapping(message.get("rescue_proposal"))
    return proposal_row(
        turn_id=turn_id,
        candidate_id=str(message.get("candidate_id") or ""),
        message_id=str(message.get("message_id") or ""),
        lifecycle_status=str(proposal.get("handoff_state") or ""),
        row_kind="active_rescue_proposal",
        active_visible=True,
        proposal_card=mapping(proposal.get("proposal_card")),
        guardrail_math=mapping(proposal.get("guardrail_math")),
        source_refs=[
            f"chat_message:{message.get('message_id') or ''}",
            f"chat_candidate:{message.get('candidate_id') or ''}",
            *[str(ref) for ref in message.get("product_runtime_output_refs") or []],
        ],
    )


def history_row(turn_id: str, packet: Mapping[str, Any]) -> dict[str, Any]:
    return proposal_row(
        turn_id=turn_id,
        candidate_id=str(packet.get("source_candidate_id") or ""),
        message_id=str(packet.get("source_message_id") or ""),
        lifecycle_status=lifecycle_status(packet),
        row_kind="rescue_proposal_history",
        active_visible=False,
        proposal_card=mapping(packet.get("proposal_card_snapshot")),
        guardrail_math=mapping(packet.get("guardrail_math_snapshot")),
        source_refs=[str(ref) for ref in packet.get("source_refs") or []],
    )


def proposal_row(
    *,
    turn_id: str,
    candidate_id: str,
    message_id: str,
    lifecycle_status: str,
    row_kind: str,
    active_visible: bool,
    proposal_card: Mapping[str, Any],
    guardrail_math: Mapping[str, Any],
    source_refs: list[str],
) -> dict[str, Any]:
    return {
        "row_kind": row_kind,
        "turn_id": turn_id,
        "candidate_id": candidate_id,
        "message_id": message_id,
        "lifecycle_status": lifecycle_status,
        "active_inbox_visible": active_visible,
        "proposal_card": dict(proposal_card),
        "concise_summary": str(proposal_card.get("headline") or "").strip(),
        "expandable_user_facing_explanation": explanation(
            proposal_card, guardrail_math
        ),
        "source_refs": [ref for ref in source_refs if ref and not ref.endswith(":")],
        "raw_trace_included": False,
        "served_to_mainline_user": False,
        "scheduler_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
    }


def explanation(
    proposal_card: Mapping[str, Any],
    guardrail_math: Mapping[str, Any],
) -> str:
    days = proposal_card.get("recommended_days") or guardrail_math.get("recommended_days")
    daily = proposal_card.get("daily_kcal_adjustment") or guardrail_math.get("daily_kcal_adjustment")
    summary = str(proposal_card.get("summary") or "").strip()
    return f"{summary} Recommended over {days} days at {abs(int(daily or 0))} kcal per day."


def lifecycle_status(packet: Mapping[str, Any]) -> str:
    if packet.get("proposal_instance_dismissed") is True:
        return "dismissed"
    if packet.get("lab_rescue_commit_pending") is True:
        return "accepted_pending_commit_confirmation"
    return str(packet.get("decision_kind") or "reviewed")


def rescue_decision_packets(
    outcomes: list[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    return [
        mapping(outcome.get("rescue_action_decision_packet"))
        for outcome in outcomes
        if mapping(outcome.get("rescue_action_decision_packet")).get("status") == "pass"
    ]


def rescue_messages(turn_artifact: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    surface = mapping(turn_artifact.get("lab_chat_surface"))
    return [
        message
        for message in surface.get("messages") or []
        if isinstance(message, Mapping)
        and message.get("workflow_family") == "rescue"
        and mapping(message.get("rescue_proposal"))
    ]


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "active_row",
    "history_row",
    "rescue_decision_packets",
    "rescue_messages",
]
