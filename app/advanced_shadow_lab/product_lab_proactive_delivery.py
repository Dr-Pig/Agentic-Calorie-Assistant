from __future__ import annotations

from typing import Any, Mapping


def build_product_lab_proactive_delivery_packet(
    *,
    candidates: list[Mapping[str, Any]],
    blocked: bool,
    contextual_send_skip_artifact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_ids = [str(candidate.get("trigger_type") or "") for candidate in candidates]
    send_skip = _mapping(contextual_send_skip_artifact)
    return {
        "artifact_type": "advanced_product_lab_proactive_delivery_packet",
        "status": "blocked" if blocked else "pass",
        "delivery_surface": "chat",
        "candidate_ids": candidate_ids,
        "send_candidate_ids": [str(candidate.get("candidate_id") or "") for candidate in candidates],
        "skipped_candidate_ids": [
            str(item) for item in send_skip.get("skip_candidate_ids") or []
        ],
        "contextual_send_skip_applied": send_skip.get("status") == "pass",
        "chat_first_delivery_records": [
            _delivery_record(candidate, send_skip) for candidate in candidates
        ],
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


def _delivery_record(
    candidate: Mapping[str, Any],
    contextual_send_skip_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id") or "")
    return {
        "candidate_id": candidate_id,
        "trigger_type": str(candidate.get("trigger_type") or ""),
        "chat_first_copy": _chat_first_copy(candidate_id, contextual_send_skip_artifact),
        "delivery_surface": "chat",
        "served_to_mainline_user": False,
        "notification_delivery_allowed": False,
        "scheduler_delivery_allowed": False,
    }


def _chat_first_copy(candidate_id: str, artifact: Mapping[str, Any]) -> str:
    for decision in artifact.get("decisions") or []:
        row = _mapping(decision)
        if row.get("candidate_id") == candidate_id:
            return str(row.get("chat_first_copy") or "")
    return ""


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_product_lab_proactive_delivery_packet"]
