from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
from typing import Any

from ...logging import REQUEST_TRACE_DIR, write_request_trace_artifact
from ..infrastructure.trace.stage_trace_store import stage_trace_path

_TRACE_MAX_ITEMS = 24
_TRACE_MAX_DICT_KEYS = 40
_TRACE_MAX_STRING_CHARS = 1000


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, str) and len(value) > _TRACE_MAX_STRING_CHARS:
            return value[:_TRACE_MAX_STRING_CHARS] + "...[truncated]"
        return value
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump(mode="json"))
    if isinstance(value, dict):
        items = list(value.items())
        serialized = {str(key): _json_safe(item) for key, item in items[:_TRACE_MAX_DICT_KEYS]}
        if len(items) > _TRACE_MAX_DICT_KEYS:
            serialized["_truncated_key_count"] = len(items) - _TRACE_MAX_DICT_KEYS
        return serialized
    if isinstance(value, (list, tuple)):
        serialized = [_json_safe(item) for item in value[:_TRACE_MAX_ITEMS]]
        if len(value) > _TRACE_MAX_ITEMS:
            serialized.append({"_truncated_item_count": len(value) - _TRACE_MAX_ITEMS})
        return serialized
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _summarize_estimated_nutrition_artifact(artifact: Any) -> dict[str, Any] | None:
    if artifact is None:
        return None
    payload = getattr(artifact, "payload", None)
    request = getattr(artifact, "request", None)
    runtime_context = getattr(artifact, "runtime_context", None)
    user = getattr(runtime_context, "user", None) if runtime_context is not None else None
    latest_log = getattr(runtime_context, "latest_log", None) if runtime_context is not None else None
    conversation_state = getattr(runtime_context, "conversation_state", None) if runtime_context is not None else None
    return {
        "request": {
            "user_id": getattr(request, "user_id", None),
            "text": getattr(request, "text", None),
            "allow_search": getattr(request, "allow_search", None),
        },
        "runtime_context": {
            "user_id": getattr(user, "id", None),
            "latest_log_id": getattr(latest_log, "id", None),
            "conversation_state_id": getattr(conversation_state, "id", None),
            "incoming_user_message_id": getattr(runtime_context, "incoming_user_message_id", None)
            if runtime_context is not None
            else None,
        },
        "payload": _json_safe(payload),
    }


def _summarize_persist_meal_log_result(result: Any) -> dict[str, Any] | None:
    if result is None:
        return None
    if isinstance(result, dict):
        return _json_safe(result)
    return {
        "action": getattr(result, "action", None),
        "status": getattr(result, "status", None),
        "persisted_log_id": getattr(result, "persisted_log_id", None),
        "linked_meal_log_id": getattr(result, "linked_meal_log_id", None),
        "canonical_commit": _json_safe(getattr(result, "canonical_commit", None)),
    }


def build_trace_refs(*, request_id: str) -> dict[str, Any]:
    return {"request_id": request_id}


def build_internal_trace_refs(*, request_id: str) -> dict[str, Any]:
    request_trace = REQUEST_TRACE_DIR / f"{request_id}.json"
    stage_trace = stage_trace_path(request_id)
    return {
        "request_id": request_id,
        "admin_trace_url": f"/admin/trace/{request_id}",
        "request_trace_path": str(request_trace),
        "request_trace_exists": request_trace.exists(),
        "stage_trace_path": str(stage_trace),
        "stage_trace_exists": stage_trace.exists(),
    }


def write_intake_turn_trace_artifact(
    *,
    request_id: str,
    user_external_id: str,
    local_date: str,
    raw_user_input: str | None,
    onboarding_payload: Any,
    allow_search: bool,
    state_before: Any,
    manager_decision: Any,
    onboarding_result: Any,
    nutrition_artifact: Any,
    persistence_result: Any,
    remaining_budget: Any,
    state_after: Any,
    assistant_message: str,
    sidecar: dict[str, Any],
    state_delta: dict[str, Any],
    phase_a_trace: dict[str, Any] | None = None,
    latency_tracking: dict[str, Any] | None = None,
) -> Path:
    payload = {
        "request_id": request_id,
        "trace_meta": {
            "request_id": request_id,
            "user_id": user_external_id,
            "bundle": "intake_turn",
            "local_date": local_date,
        },
        "request": {
            "user_id": user_external_id,
            "local_date": local_date,
            "text": raw_user_input,
            "allow_search": allow_search,
            "onboarding_payload": _json_safe(onboarding_payload),
        },
        "state_before": _json_safe(state_before),
        "manager_decision": _json_safe(manager_decision),
        "tool_outputs": {
            "onboarding_result": _json_safe(onboarding_result),
            "nutrition_artifact": _summarize_estimated_nutrition_artifact(nutrition_artifact),
            "persistence_result": _summarize_persist_meal_log_result(persistence_result),
            "remaining_budget": _json_safe(remaining_budget),
        },
        "state_after": _json_safe(state_after),
        "renderer_output": {"assistant_message": assistant_message},
        "sidecar_output": _json_safe(sidecar),
        "state_delta": _json_safe(state_delta),
        "phase_a_trace": _json_safe(phase_a_trace or {}),
        "latency_tracking": latency_tracking or {},
        "trace_refs": build_internal_trace_refs(request_id=request_id),
    }
    return write_request_trace_artifact(request_id, payload)


def write_intake_execution_trace_artifact(
    *,
    request_id: str,
    user_external_id: str,
    local_date: str,
    raw_user_input: str | None,
    allow_search: bool,
    state_before: Any,
    manager_round_1: Any,
    injected_context_summary: dict[str, Any],
    tool_plan: list[str],
    tool_outputs: dict[str, Any],
    manager_final_decision: Any,
    state_after: Any,
    assistant_message: str,
    sidecar: dict[str, Any],
    state_delta: dict[str, Any],
    phase_a_trace: dict[str, Any] | None = None,
    phase_c_trace: dict[str, Any] | None = None,
    react_trace: dict[str, Any] | None = None,
    latency_tracking: dict[str, Any] | None = None,
) -> Path:
    serialized_round_1 = _json_safe(manager_round_1)
    serialized_final_decision = _json_safe(manager_final_decision)
    payload = {
        "request_id": request_id,
        "trace_meta": {
            "request_id": request_id,
            "user_id": user_external_id,
            "bundle": "intake_execution",
            "local_date": local_date,
        },
        "request": {
            "user_id": user_external_id,
            "local_date": local_date,
            "text": raw_user_input,
            "allow_search": allow_search,
        },
        "state_before": _json_safe(state_before),
        "manager_rounds": [
            {
                "round": 1,
                "decision": serialized_round_1,
            }
        ],
        "manager_final_decision": serialized_final_decision,
        "injected_context_summary": _json_safe(injected_context_summary),
        "tool_plan": _json_safe(tool_plan),
        "tool_outputs": _json_safe(tool_outputs),
        "state_after": _json_safe(state_after),
        "renderer_output": {"assistant_message": assistant_message},
        "sidecar_output": _json_safe(sidecar),
        "state_delta": _json_safe(state_delta),
        "phase_a_trace": _json_safe(phase_a_trace or {}),
        "phase_c_trace": _json_safe(phase_c_trace or {}),
        "react_trace": _json_safe(react_trace or {}),
        "latency_tracking": latency_tracking or {},
        "trace_refs": build_internal_trace_refs(request_id=request_id),
    }
    return write_request_trace_artifact(request_id, payload)


def write_general_chat_request_trace_artifact(
    *,
    request_id: str,
    user_external_id: str,
    local_date: str,
    raw_user_input: str | None,
    state_before: Any,
    general_chat_result: Any,
    assistant_message: str,
    phase_a_trace: dict[str, Any] | None = None,
) -> Path:
    payload = {
        "request_id": request_id,
        "trace_meta": {
            "request_id": request_id,
            "user_id": user_external_id,
            "bundle": "v2_general_chat",
            "local_date": local_date,
        },
        "request": {
            "user_id": user_external_id,
            "local_date": local_date,
            "text": raw_user_input,
        },
        "state_before": _json_safe(state_before),
        "general_chat_result": _json_safe(general_chat_result),
        "renderer_output": {"assistant_message": assistant_message},
        "phase_a_trace": _json_safe(phase_a_trace or {}),
        "trace_refs": build_internal_trace_refs(request_id=request_id),
    }
    return write_request_trace_artifact(request_id, payload)
