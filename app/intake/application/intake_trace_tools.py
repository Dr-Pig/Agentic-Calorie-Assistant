from __future__ import annotations

from typing import Any

from ...logging import now_iso
from ...runtime.infrastructure.trace.stage_trace_store import append_stage_trace_event
from .intake_tool_runtime import conversation_pending_followup, json_safe, normalize_live_payload

_normalize_intake_live_payload = normalize_live_payload


def append_trace_event_tool(
    *,
    request_id: str,
    stage: str,
    status: str,
    summary: dict[str, Any],
) -> None:
    append_stage_trace_event(
        request_id,
        {
            "request_id": request_id,
            "stage": stage,
            "status": status,
            "timestamp": now_iso(),
            "summary": json_safe(summary),
        },
    )


def resolve_correction_target_tool(
    *,
    resolved_state: Any,
) -> dict[str, Any]:
    target = ((resolved_state.injected_context or {}).get("TARGET_MEAL_REFERENCE") or {}).copy()
    pending = conversation_pending_followup(getattr(resolved_state, "conversation_state", None))
    if pending.get("is_open"):
        target["target_resolution_source"] = "pending_followup_state"
        target["correction_confidence"] = "high"
    return target
