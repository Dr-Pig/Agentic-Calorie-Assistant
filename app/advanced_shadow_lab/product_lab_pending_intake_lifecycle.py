from __future__ import annotations

from typing import Any, Mapping


TERMINAL_ACTIONS = {
    "confirm_pending_intake": "confirmed_lab_intake",
    "cancel_pending_intake": "canceled_lab_intake",
}


def build_pending_intake_lifecycle_packet(
    *,
    message: Mapping[str, Any],
    action: str,
) -> dict[str, Any]:
    draft_ids = [
        str(item) for item in message.get("pending_intake_draft_ids") or []
    ]
    target_draft_id = draft_ids[0] if draft_ids else ""
    terminal_state = TERMINAL_ACTIONS.get(action, "unsupported_pending_intake_action")
    blockers = _blockers(
        action=action,
        message=message,
        target_draft_id=target_draft_id,
    )
    return {
        "artifact_type": "advanced_product_lab_pending_intake_lifecycle_packet",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "action": action,
        "terminal_state": terminal_state,
        "target_draft_id": target_draft_id,
        "source_message_id": str(message.get("message_id") or ""),
        "source_candidate_id": str(message.get("candidate_id") or ""),
        "actual_intake_observed": action == "confirm_pending_intake" and not blockers,
        "meal_thread_mutated": False,
        "ledger_entry_created": False,
        "canonical_product_mutation_allowed": False,
        "served_to_mainline_user": False,
        "scheduler_delivery_allowed": False,
        "durable_product_memory_written": False,
        "source_refs": [
            f"chat_message:{message.get('message_id') or ''}",
            f"pending_intake_draft:{target_draft_id}",
            *[str(ref) for ref in message.get("product_runtime_output_refs") or []],
        ],
        "blockers": blockers,
    }


def _blockers(
    *,
    action: str,
    message: Mapping[str, Any],
    target_draft_id: str,
) -> list[str]:
    blockers: list[str] = []
    if action not in TERMINAL_ACTIONS:
        blockers.append(f"pending_intake.action_unsupported:{action}")
    if message.get("workflow_family") != "pending_intake":
        blockers.append("pending_intake.workflow_family_mismatch")
    if not target_draft_id:
        blockers.append("pending_intake.target_draft_id_missing")
    if message.get("canonical_mutation_requested") is True:
        blockers.append("pending_intake.chat_message_canonical_mutation_requested")
    return blockers


__all__ = ["build_pending_intake_lifecycle_packet"]
