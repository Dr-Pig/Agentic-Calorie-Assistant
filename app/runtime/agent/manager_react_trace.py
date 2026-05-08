from __future__ import annotations

from typing import Any

from app.runtime.agent.manager_payload_utils import json_safe


MANAGER_REACT_TRACE_SCHEMA_VERSION = "manager_react_trace.v1"


def _tool_name(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    name = str(value.get("name") or value.get("tool_name") or "").strip()
    return name or None


def _round_summary(round_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(round_payload, dict):
        return None
    decision = dict(round_payload.get("decision") or {})
    return {
        "round_index": round_payload.get("round_index"),
        "stage": round_payload.get("stage"),
        "manager_action": decision.get("manager_action"),
        "final_action": decision.get("final_action"),
        "workflow_effect": decision.get("workflow_effect"),
        "tool_calls": json_safe(list(decision.get("tool_calls") or [])),
        "decision_payload": json_safe(decision),
        "provider_trace": json_safe(dict(round_payload.get("trace") or {})),
        "prompt_registry": json_safe(dict(round_payload.get("prompt_registry") or {})),
        "prompt_layer_contract": json_safe(dict(round_payload.get("prompt_layer_contract") or {})),
    }


def _compact_round_summary(round_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(round_payload, dict):
        return None
    decision = dict(round_payload.get("decision") or {})
    tool_names: list[str] = []
    for tool_call in list(decision.get("tool_calls") or []):
        tool_name = _tool_name(tool_call)
        if tool_name:
            tool_names.append(tool_name)
    return {
        "round_index": round_payload.get("round_index"),
        "stage": round_payload.get("stage"),
        "manager_action": decision.get("manager_action"),
        "final_action": decision.get("final_action"),
        "workflow_effect": decision.get("workflow_effect"),
        "tool_names": tool_names,
    }


def build_manager_react_trace(
    *,
    manager_rounds: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    guard_outcome: dict[str, Any] | None,
    failure_family: str | None,
) -> dict[str, Any]:
    requested_tools: list[str] = []
    for round_payload in manager_rounds:
        if not isinstance(round_payload, dict):
            continue
        decision = dict(round_payload.get("decision") or {})
        for tool_call in list(decision.get("tool_calls") or []):
            tool_name = _tool_name(tool_call)
            if tool_name and tool_name not in requested_tools:
                requested_tools.append(tool_name)

    executed_tools: list[str] = []
    for result in tool_results:
        tool_name = _tool_name(result)
        if tool_name and tool_name not in executed_tools:
            executed_tools.append(tool_name)

    manager_pass_summaries = [summary for summary in (_compact_round_summary(round_payload) for round_payload in manager_rounds) if summary]
    first_round_summary = _round_summary(manager_rounds[0]) if manager_rounds else None
    final_round_summary = _round_summary(manager_rounds[-1]) if manager_rounds else None

    return {
        "trace_schema_version": MANAGER_REACT_TRACE_SCHEMA_VERSION,
        "manager_pass_count": len(manager_pass_summaries),
        "manager_pass_1": first_round_summary,
        "manager_passes": manager_pass_summaries,
        "requested_tools": requested_tools,
        "executed_tools": executed_tools,
        "manager_pass_final": final_round_summary,
        "guard_result": json_safe(dict(guard_outcome or {})),
        "request_failure_family": failure_family,
    }


__all__ = ["MANAGER_REACT_TRACE_SCHEMA_VERSION", "build_manager_react_trace"]
