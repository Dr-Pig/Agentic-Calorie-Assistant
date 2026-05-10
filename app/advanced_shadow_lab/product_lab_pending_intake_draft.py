from __future__ import annotations

from typing import Any, Mapping


def build_pending_intake_draft_packet(
    *,
    message: Mapping[str, Any],
    action: str,
) -> dict[str, Any]:
    offer = _mapping(message.get("recommendation_offer"))
    primary_id = str(offer.get("primary_candidate_id") or "")
    snapshot = _mapping(offer.get("candidate_snapshot"))
    blockers = _blockers(
        action=action,
        offer=offer,
        primary_id=primary_id,
        snapshot=snapshot,
        message=message,
    )
    return {
        "artifact_type": "advanced_product_lab_pending_intake_draft_packet",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "draft_state": "pending_user_intake_confirmation",
        "draft_kind": "recommendation_selected_candidate",
        "source_message_id": str(message.get("message_id") or ""),
        "source_candidate_id": str(message.get("candidate_id") or ""),
        "primary_candidate_id": primary_id,
        "selected_candidate_snapshot": dict(snapshot),
        "intake_handoff_state": str(offer.get("intake_handoff_state") or ""),
        "requires_explicit_user_intake_action": (
            offer.get("requires_explicit_user_intake_action") is True
        ),
        "requires_followup_commit_confirmation": True,
        "actual_intake_observed": False,
        "canonical_commit_requested": offer.get("canonical_commit_requested") is True,
        "canonical_product_mutation_allowed": False,
        "meal_thread_mutated": False,
        "ledger_entry_created": False,
        "served_to_mainline_user": False,
        "durable_product_memory_written": False,
        "lab_pending_intake_draft_created": not blockers,
        "source_refs": _source_refs(message, primary_id, snapshot, offer),
        "blockers": blockers,
    }


def _blockers(
    *,
    action: str,
    offer: Mapping[str, Any],
    primary_id: str,
    snapshot: Mapping[str, Any],
    message: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if action != "log_this":
        blockers.append(f"action_not_pending_intake_draft:{action}")
    if not primary_id:
        blockers.append("recommendation_offer.primary_candidate_id_missing")
    if not snapshot:
        blockers.append("recommendation_offer.candidate_snapshot_missing")
    if offer.get("intake_handoff_state") != "pending_user_intake_confirmation":
        blockers.append("recommendation_offer.handoff_state_not_pending_confirmation")
    if offer.get("requires_explicit_user_intake_action") is not True:
        blockers.append("recommendation_offer.explicit_intake_action_not_required")
    if offer.get("canonical_commit_requested") is True:
        blockers.append("recommendation_offer.canonical_commit_requested")
    if message.get("canonical_mutation_requested") is True:
        blockers.append("chat_message.canonical_mutation_requested")
    return blockers


def _source_refs(
    message: Mapping[str, Any],
    primary_id: str,
    snapshot: Mapping[str, Any],
    offer: Mapping[str, Any],
) -> list[str]:
    refs = [
        f"chat_message:{message.get('message_id') or ''}",
        f"chat_candidate:{message.get('candidate_id') or ''}",
        f"recommendation_candidate:{primary_id}",
        f"handoff_artifact:{offer.get('source_pending_intake_handoff_artifact_type') or ''}",
    ]
    refs.extend(str(item) for item in snapshot.get("source_refs") or [])
    return [ref for ref in refs if not ref.endswith(":")]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_pending_intake_draft_packet"]
