from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping

from app.memory.application.runtime_lab_trace_ingress_contracts import (
    REQUIRED_SCOPE_KEYS,
)


def resolve_scope_keys(
    trace: Mapping[str, Any],
    scope_overrides: Mapping[str, str],
) -> dict[str, str]:
    trace_scope = mapping(trace.get("memory_lab_scope"))
    request = mapping(trace.get("request"))
    trace_meta = mapping(trace.get("trace_meta"))
    run_id = (
        scope_overrides.get("run_id")
        or trace_scope.get("run_id")
        or trace_meta.get("run_id")
    )
    return {
        "user_id": str(
            scope_overrides.get("user_id")
            or trace_scope.get("user_id")
            or trace_meta.get("user_id")
            or request.get("user_id")
            or ""
        ),
        "workspace_id": str(
            scope_overrides.get("workspace_id") or trace_scope.get("workspace_id") or ""
        ),
        "project_id": str(
            scope_overrides.get("project_id") or trace_scope.get("project_id") or ""
        ),
        "surface": str(
            scope_overrides.get("surface") or trace_scope.get("surface") or ""
        ),
        "run_id": str(run_id or ""),
    }


def request_id(trace: Mapping[str, Any]) -> str:
    return str(
        dig(trace, "trace_meta", "request_id")
        or trace.get("request_id")
        or dig(trace, "trace_refs", "request_id")
        or "unknown-request"
    )


def source_trace_ids(trace: Mapping[str, Any], resolved_request_id: str) -> list[str]:
    trace_refs = mapping(trace.get("trace_refs"))
    ids = [resolved_request_id]
    for key in ("request_trace_path", "stage_trace_path"):
        value = trace_refs.get(key)
        if value:
            ids.append(str(value))
    return dedupe(ids)


def canonical_source_refs(
    trace: Mapping[str, Any],
    resolved_request_id: str,
) -> list[dict[str, str]]:
    refs = [
        {
            "source_type": "runtime_request_trace",
            "source_id": resolved_request_id,
            "field_path": "request_id",
        }
    ]
    final_decision = trace.get("manager_final_decision") or trace.get("manager_decision")
    if isinstance(final_decision, Mapping):
        refs.append(
            {
                "source_type": "manager_decision",
                "source_id": resolved_request_id,
                "field_path": (
                    "manager_final_decision"
                    if "manager_final_decision" in trace
                    else "manager_decision"
                ),
            }
        )
    persisted_log_id = dig(
        trace,
        "tool_outputs",
        "persistence_result",
        "persisted_log_id",
    )
    if persisted_log_id:
        refs.append(
            {
                "source_type": "meal_thread",
                "source_id": str(persisted_log_id),
                "field_path": "tool_outputs.persistence_result.persisted_log_id",
            }
        )
    for name in tool_call_names(trace):
        refs.append(
            {
                "source_type": "tool_call_or_output",
                "source_id": name,
                "field_path": "tool_plan",
            }
        )
    return refs


def manager_decision_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    decision = trace.get("manager_final_decision") or trace.get("manager_decision") or {}
    decision_mapping = mapping(decision)
    keys = (
        "intent",
        "workflow_effect",
        "manager_action",
        "final_action",
        "target_attachment",
        "exactness",
        "confidence",
    )
    return {key: decision_mapping.get(key) for key in keys if key in decision_mapping}


def tool_call_names(trace: Mapping[str, Any]) -> list[str]:
    names: list[str] = []
    tool_plan = trace.get("tool_plan")
    if isinstance(tool_plan, list):
        names.extend(str(item) for item in tool_plan if item)
    tool_outputs = trace.get("tool_outputs")
    if isinstance(tool_outputs, Mapping):
        names.extend(str(key) for key in tool_outputs)
    return dedupe(names)


def event_id(scope_keys: Mapping[str, str], resolved_request_id: str) -> str:
    raw = (
        "|".join(scope_keys[key] for key in REQUIRED_SCOPE_KEYS)
        + f"|{resolved_request_id}"
    )
    return "memory-ingress-" + sha256(raw.encode("utf-8")).hexdigest()[:16]


def dig(value: Mapping[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


__all__ = [
    "canonical_source_refs",
    "dig",
    "event_id",
    "manager_decision_summary",
    "request_id",
    "resolve_scope_keys",
    "source_trace_ids",
    "tool_call_names",
]
