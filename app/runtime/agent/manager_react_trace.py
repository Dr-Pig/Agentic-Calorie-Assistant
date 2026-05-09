from __future__ import annotations

from typing import Any

from app.runtime.agent.manager_payload_utils import json_safe


MANAGER_REACT_TRACE_SCHEMA_VERSION = "manager_react_trace.v1"


def _tool_name(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    name = str(value.get("name") or value.get("tool_name") or "").strip()
    return name or None


def _duration_ms(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _round_summary(round_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(round_payload, dict):
        return None
    decision = dict(round_payload.get("decision") or {})
    return {
        "round_index": round_payload.get("round_index"),
        "stage": round_payload.get("stage"),
        "latency_ms": _duration_ms(round_payload.get("latency_ms")),
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
        "latency_ms": _duration_ms(round_payload.get("latency_ms")),
        "manager_action": decision.get("manager_action"),
        "final_action": decision.get("final_action"),
        "workflow_effect": decision.get("workflow_effect"),
        "tool_names": tool_names,
    }


def _topology_events(value: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for item in value or []:
        if not isinstance(item, dict):
            continue
        event: dict[str, Any] = {
            "operation": str(item.get("operation") or ""),
            "stage": str(item.get("stage") or ""),
            "duration_ms": _duration_ms(item.get("duration_ms")),
        }
        if item.get("round_index") is not None:
            event["round_index"] = item.get("round_index")
        tool_names = [name for name in (_tool_name(tool_call) for tool_call in list(item.get("tool_calls") or [])) if name]
        if not tool_names and isinstance(item.get("tool_names"), list):
            tool_names = [str(name) for name in item["tool_names"] if str(name).strip()]
        if tool_names:
            event["tool_names"] = tool_names
        if item.get("tool_count") is not None:
            event["tool_count"] = _duration_ms(item.get("tool_count"))
        if item.get("guard_ok") is not None:
            event["guard_ok"] = bool(item.get("guard_ok"))
        if item.get("failure_family") not in (None, ""):
            event["failure_family"] = str(item.get("failure_family"))
        events.append({key: value for key, value in event.items() if value not in ("", [], {})})
    return events


def build_manager_react_trace(
    *,
    manager_rounds: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    guard_outcome: dict[str, Any] | None,
    failure_family: str | None,
    call_topology: list[dict[str, Any]] | None = None,
    repair_round_used: bool = False,
    total_latency_ms: int | None = None,
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
    manager_round_latency_ms = [_duration_ms(summary.get("latency_ms")) for summary in manager_pass_summaries]
    topology = _topology_events(call_topology)
    tool_batch_latency_ms = sum(_duration_ms(event.get("duration_ms")) for event in topology if event.get("operation") == "tool_batch")
    guard_latency_ms = sum(_duration_ms(event.get("duration_ms")) for event in topology if event.get("operation") == "guard_check")
    tool_call_count = sum(_duration_ms(event.get("tool_count")) for event in topology if event.get("operation") == "tool_batch")
    component_latency_ms = sum(manager_round_latency_ms) + tool_batch_latency_ms + guard_latency_ms
    observed_total_latency_ms = max(_duration_ms(total_latency_ms), component_latency_ms)

    return {
        "trace_schema_version": MANAGER_REACT_TRACE_SCHEMA_VERSION,
        "manager_pass_count": len(manager_pass_summaries),
        "manager_round_count": len(manager_pass_summaries),
        "manager_round_latency_ms": manager_round_latency_ms,
        "tool_batch_latency_ms": tool_batch_latency_ms,
        "guard_latency_ms": guard_latency_ms,
        "total_latency_ms": observed_total_latency_ms,
        "orchestration_latency_ms": max(0, observed_total_latency_ms - component_latency_ms),
        "tool_call_count": tool_call_count,
        "repair_round_used": bool(repair_round_used),
        "call_topology": topology,
        "manager_pass_1": first_round_summary,
        "manager_passes": manager_pass_summaries,
        "requested_tools": requested_tools,
        "executed_tools": executed_tools,
        "manager_pass_final": final_round_summary,
        "guard_result": json_safe(dict(guard_outcome or {})),
        "request_failure_family": failure_family,
    }


__all__ = ["MANAGER_REACT_TRACE_SCHEMA_VERSION", "build_manager_react_trace"]
