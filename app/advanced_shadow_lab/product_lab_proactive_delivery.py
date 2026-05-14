from __future__ import annotations

from typing import Any, Mapping


def build_product_lab_proactive_delivery_packet(
    *,
    candidates: list[Mapping[str, Any]],
    blocked: bool,
) -> dict[str, Any]:
    candidate_ids = [str(candidate.get("trigger_type") or "") for candidate in candidates]
    return {
        "artifact_type": "advanced_product_lab_proactive_delivery_packet",
        "status": "blocked" if blocked else "pass",
        "delivery_surface": "chat",
        "candidate_ids": candidate_ids,
        "chat_delivery_allowed": bool(candidates) and not blocked,
        "scheduler_delivery_attempted": False,
        "notification_delivery_attempted": False,
        "push_or_line_delivery_connected": False,
        "served_to_mainline_user": False,
        "controls_by_candidate": {
            str(candidate.get("trigger_type") or ""): controls(candidate)
            for candidate in candidates
        },
        "candidate_traces_by_candidate": {
            str(candidate.get("trigger_type") or ""): dict(
                candidate.get("pre_delivery_candidate_trace") or {}
            )
            for candidate in candidates
        },
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }


def controls(candidate: Mapping[str, Any]) -> dict[str, bool]:
    return {
        "dismiss": bool(candidate.get("dismiss_reason_choices")),
        "snooze": bool(candidate.get("snooze_window")),
        "undo": str(candidate.get("undo_scope") or "") == "candidate_instance",
    }


__all__ = ["build_product_lab_proactive_delivery_packet"]
