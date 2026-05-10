from __future__ import annotations

from typing import Any, Mapping


def build_pending_rescue_commit_packet(
    *,
    proposal_card: Mapping[str, Any],
    primary_actions: list[str],
    lifecycle_packets: list[Mapping[str, Any]],
) -> dict[str, Any]:
    blockers = [] if proposal_card else ["proposal_card.missing"]
    accepted = next(
        (
            packet
            for packet in lifecycle_packets
            if packet.get("lab_lifecycle_state")
            == "accepted_lab_pending_explicit_commit"
        ),
        {},
    )
    if not accepted:
        blockers.append("accepted_lifecycle_packet.missing")
    return {
        "artifact_type": "advanced_product_lab_pending_rescue_commit",
        "status": "blocked" if blockers else "pass",
        "handoff_state": "pending_user_rescue_commit_confirmation",
        "proposal_card": dict(proposal_card),
        "primary_actions": list(primary_actions),
        "accepted_lifecycle_packet": dict(accepted),
        "lab_rescue_intent_created": not blockers,
        "requires_explicit_user_rescue_commit": True,
        "canonical_commit_requested": False,
        "proposal_committed": False,
        "ledger_entry_created": False,
        "day_budget_mutated": False,
        "served_to_mainline_user": False,
        "blockers": blockers,
    }


__all__ = ["build_pending_rescue_commit_packet"]
