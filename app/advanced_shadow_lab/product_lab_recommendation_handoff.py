from __future__ import annotations

from typing import Any, Mapping


def build_pending_intake_handoff_packet(
    *,
    primary_candidate: Mapping[str, Any],
    ux_packet: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_id = str(primary_candidate.get("candidate_id") or "")
    blockers = [] if candidate_id else ["candidate_id.missing"]
    return {
        "artifact_type": "advanced_product_lab_pending_intake_handoff",
        "status": "blocked" if blockers else "pass",
        "handoff_state": "pending_user_intake_confirmation",
        "candidate_id": candidate_id,
        "candidate_snapshot": dict(primary_candidate),
        "offer_action": "log_this",
        "lab_intake_intent_created": not blockers,
        "requires_explicit_user_intake_action": True,
        "canonical_commit_requested": False,
        "canonical_product_mutation_allowed": False,
        "served_to_mainline_user": False,
        "source_ux_packet_primary_candidate_id": str(
            ux_packet.get("primary_candidate_id") or ""
        ),
        "blockers": blockers,
    }


__all__ = ["build_pending_intake_handoff_packet"]
