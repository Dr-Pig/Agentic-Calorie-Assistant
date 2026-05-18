from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_runtime_turn_lifecycle(
    *,
    phase_a_trace: dict[str, Any],
    final_mapping: dict[str, Any],
    sidecar: dict[str, Any],
) -> dict[str, Any]:
    status = runtime_turn_status_from_inputs(
        phase_a_trace=phase_a_trace,
        final_mapping=final_mapping,
    )
    queue_lifecycle = _dict_or_empty(phase_a_trace.get("queue_lifecycle"))
    queued_after_request_id = (
        queue_lifecycle.get("queued_after_request_id")
        or queue_lifecycle.get("enqueued_after_request_id")
        or phase_a_trace.get("queued_after_request_id")
        or sidecar.get("queued_after_request_id")
    )
    is_terminal = status not in {"in_progress", "queued"}
    lifecycle = {
        "status": status,
        "initial_status": status,
        "was_queued": status == "queued" or queued_after_request_id is not None,
        "queued_after_request_id": str(queued_after_request_id) if queued_after_request_id is not None else None,
        "accepted_at": queue_lifecycle.get("accepted_at") or utc_now_iso(),
        "enqueued_at": queue_lifecycle.get("enqueued_at") if queued_after_request_id is not None else None,
        "dequeued_at": None,
        "terminal_state": is_terminal,
        "trace_role": "durable_turn_ordering_not_semantic_owner",
    }
    if status == "queued" and lifecycle["enqueued_at"] is None:
        lifecycle["enqueued_at"] = lifecycle["accepted_at"]
    return lifecycle


def runtime_turn_status_from_inputs(
    *,
    phase_a_trace: dict[str, Any],
    final_mapping: dict[str, Any],
) -> str:
    phase_status = str(phase_a_trace.get("runtime_turn_status") or "").strip()
    if phase_status in {"in_progress", "queued", "failed"}:
        return phase_status
    final_action = str(final_mapping.get("final_action") or "").strip()
    if final_action == "queued":
        return "queued"
    if final_action == "pending":
        return "in_progress"
    if final_action:
        return "completed"
    return "not_available"


def existing_runtime_lifecycle_from_messages(messages: list[Any]) -> dict[str, Any]:
    for message in messages:
        trace_json = message.trace_json if isinstance(message.trace_json, dict) else {}
        trace = trace_json.get("runtime_turn_trace")
        if not isinstance(trace, dict):
            continue
        lifecycle = trace.get("runtime_turn_lifecycle")
        if isinstance(lifecycle, dict):
            return dict(lifecycle)
    return {}


def apply_runtime_turn_lifecycle_merge(
    trace: dict[str, Any],
    *,
    existing_messages: list[Any],
) -> None:
    prior = existing_runtime_lifecycle_from_messages(existing_messages)
    current = _dict_or_empty(trace.get("runtime_turn_lifecycle"))
    trace["runtime_turn_lifecycle"] = merge_runtime_turn_lifecycle(current, prior=prior)


def merge_runtime_turn_lifecycle(
    current: dict[str, Any],
    *,
    prior: dict[str, Any],
) -> dict[str, Any]:
    if not prior:
        return current
    status = str(current.get("status") or "not_available")
    was_queued = bool(prior.get("was_queued") is True or current.get("was_queued") is True)
    merged = {
        **prior,
        **current,
        "initial_status": prior.get("initial_status") or current.get("initial_status") or status,
        "was_queued": was_queued,
        "queued_after_request_id": current.get("queued_after_request_id") or prior.get("queued_after_request_id"),
        "enqueued_at": prior.get("enqueued_at") or current.get("enqueued_at"),
        "accepted_at": prior.get("accepted_at") or current.get("accepted_at"),
        "terminal_state": status not in {"in_progress", "queued"},
        "trace_role": "durable_turn_ordering_not_semantic_owner",
    }
    if was_queued and merged["terminal_state"] and not merged.get("dequeued_at"):
        merged["dequeued_at"] = utc_now_iso()
    return merged


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


__all__ = [
    "apply_runtime_turn_lifecycle_merge",
    "build_runtime_turn_lifecycle",
    "existing_runtime_lifecycle_from_messages",
    "merge_runtime_turn_lifecycle",
    "runtime_turn_status_from_inputs",
]
