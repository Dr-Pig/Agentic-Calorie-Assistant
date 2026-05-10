from __future__ import annotations

from typing import Any, Mapping


def pending_intake_chat_packets(
    *,
    product_proactive: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        _packet(index, candidate)
        for index, candidate in enumerate(product_proactive.get("candidates") or [])
        if isinstance(candidate, Mapping)
        and candidate.get("trigger_type") == "pending_intake_followup"
    ]


def _packet(index: int, candidate: Mapping[str, Any]) -> dict[str, Any]:
    draft_ids = _draft_ids(candidate)
    return {
        "packet_id": str(candidate.get("candidate_id") or f"pending_intake_followup:{index + 2}"),
        "surface": "chat",
        "chat_first": True,
        "packet_kind": "pending_intake_confirmation_followup",
        "workflow_family": "pending_intake",
        "trigger_type": "pending_intake_followup",
        "candidate_kind": str(candidate.get("candidate_kind") or ""),
        "pending_intake_draft_ids": draft_ids,
        "product_runtime_output_refs": [
            str(item) for item in candidate.get("source_output_refs") or []
        ],
        "product_lab_copy": "Confirm or cancel the pending intake draft.",
        "controls": {
            "dismiss_reason_required": bool(candidate.get("dismiss_reason_choices")),
            "snooze_window_present": bool(candidate.get("snooze_window")),
            "undo_scope": str(candidate.get("undo_scope") or ""),
        },
        "next_signal_required": str(candidate.get("next_signal_required") or ""),
        "served_to_user": False,
        "delivery_attempted": False,
        "scheduler_enqueued": False,
        "canonical_mutation_requested": False,
    }


def _draft_ids(candidate: Mapping[str, Any]) -> list[str]:
    prefix = "pending_intake_draft:"
    return [
        str(ref)[len(prefix) :]
        for ref in candidate.get("source_output_refs") or []
        if str(ref).startswith(prefix)
    ]


__all__ = ["pending_intake_chat_packets"]
