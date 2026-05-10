from __future__ import annotations

from typing import Any, Mapping


def build_pending_intake_handoff_packet(
    *,
    primary_candidate: Mapping[str, Any],
    ux_packet: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_id = str(primary_candidate.get("candidate_id") or "")
    omitted = not candidate_id
    return {
        "artifact_type": "advanced_product_lab_pending_intake_handoff",
        "status": "omitted" if omitted else "pass",
        "handoff_state": "no_pending_intake_handoff"
        if omitted
        else "pending_user_intake_confirmation",
        "candidate_id": candidate_id,
        "candidate_snapshot": dict(primary_candidate),
        "offer_action": "log_this",
        "lab_intake_intent_created": not omitted,
        "requires_explicit_user_intake_action": True,
        "canonical_commit_requested": False,
        "canonical_product_mutation_allowed": False,
        "served_to_mainline_user": False,
        "source_ux_packet_primary_candidate_id": str(
            ux_packet.get("primary_candidate_id") or ""
        ),
        "omission_reason": "no_qualified_candidate" if omitted else "",
        "blockers": [],
    }


__all__ = ["build_pending_intake_handoff_packet"]
