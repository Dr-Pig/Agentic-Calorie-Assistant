from __future__ import annotations

from typing import Any

from ..logging import now_iso
from ..observability.stage_trace_store import append_stage_trace_event
from ..schemas import StageTraceEvent


def logical_model_role_for_stage(stage: str) -> str:
    if stage.startswith("task_meal_link_pass") or stage.startswith("planner_pass") or stage.startswith("decision_pass"):
        return "fast_router_model"
    if stage.startswith("nutrition_resolution_pass") or stage.startswith("primary_answer_pass"):
        return "strict_reasoner_model"
    if stage.startswith("final_response_pass"):
        return "response_writer_model"
    return "strict_reasoner_model"


def append_stage_runtime_event(
    *,
    request_id: str,
    stage: str,
    provider: Any,
    merged_trace: dict[str, Any],
    trigger_reason: str | None = None,
) -> None:
    if not request_id.strip():
        return
    readiness = provider.readiness() if hasattr(provider, "readiness") else {}
    event = StageTraceEvent(
        request_id=request_id,
        stage=stage,
        status="error" if merged_trace.get("error") else "ok",
        attempt_index=int(merged_trace.get("attempt_index", 1) or 1),
        provider=merged_trace.get("provider") or readiness.get("provider"),
        provider_role=getattr(provider, "role_label", None) or readiness.get("role"),
        logical_model_role=logical_model_role_for_stage(stage),
        model_id=merged_trace.get("model"),
        timestamp=now_iso(),
        trigger_reason=trigger_reason,
        fallback_mode=merged_trace.get("fallback_mode"),
    )
    append_stage_trace_event(request_id, event.model_dump(mode="json"))
