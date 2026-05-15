from __future__ import annotations

from typing import Any


def body_observation_recorded(request_trace: dict[str, Any], state_delta: dict[str, Any]) -> bool:
    if state_delta.get("body_observation_recorded") is True:
        return True
    return _recorded_body_observation_tool_result(request_trace) is not None


def attach_body_observation_runtime_projection(
    runtime: dict[str, Any],
    *,
    request_trace: dict[str, Any],
    state_delta: dict[str, Any],
) -> None:
    tool_result = _recorded_body_observation_tool_result(request_trace)
    if not body_observation_recorded(request_trace, state_delta):
        return
    if str(runtime.get("workflow_effect") or "") == "record_weight":
        runtime["workflow_effect"] = "body_observation_write"
    runtime["mutation_allowed"] = True
    runtime.setdefault("body_plan_rewrite_allowed", False)
    runtime.setdefault("manager_tdee_math_allowed", False)
    if tool_result is not None:
        mutation_result = _dict(tool_result.get("mutation_result"))
        if mutation_result.get("body_plan_mutated") is False:
            runtime["body_plan_rewrite_allowed"] = False
        if mutation_result.get("ledger_mutated") is False:
            runtime["manager_tdee_math_allowed"] = False


def attach_body_observation_ui_projection(
    ui: dict[str, Any],
    *,
    request_trace: dict[str, Any],
    state_delta: dict[str, Any],
) -> None:
    if not body_observation_recorded(request_trace, state_delta):
        return
    recorded = _dict(_dict(_recorded_body_observation_tool_result(request_trace)).get("evidence")).get(
        "recorded_body_observation"
    )
    if isinstance(recorded, dict) and recorded.get("value") is not None:
        ui.setdefault("latest_weight_visible", True)
    if isinstance(recorded, dict) and recorded.get("local_date"):
        ui.setdefault("weight_history_date_scoped", True)
    active_plan = _dict(_dict(request_trace.get("state_after")).get("active_body_plan_view"))
    if active_plan:
        ui.setdefault("body_plan_date_scoped", False)
        ui.setdefault("body_form_prefilled_from_saved_truth", True)
    ui.setdefault("frontend_tdee_math_allowed", False)


def _recorded_body_observation_tool_result(request_trace: dict[str, Any]) -> dict[str, Any] | None:
    candidates: list[Any] = []
    tool_outputs = _dict(request_trace.get("tool_outputs"))
    if tool_outputs.get("persistence_result") is not None:
        candidates.append(tool_outputs.get("persistence_result"))
    candidates.extend(_list(tool_outputs.get("tool_results")))
    manager_decision = _dict(request_trace.get("manager_decision"))
    candidates.extend(_list(manager_decision.get("tool_results")))
    for item in candidates:
        payload = _dict(item)
        if not payload:
            continue
        provenance = _dict(payload.get("provenance"))
        tool_name = str(provenance.get("canonical_tool_name") or payload.get("tool_name") or "").strip()
        mutation_result = _dict(payload.get("mutation_result"))
        if tool_name == "body.record_observation" and mutation_result.get("body_observation_recorded") is True:
            return payload
    return None


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


__all__ = [
    "attach_body_observation_runtime_projection",
    "attach_body_observation_ui_projection",
    "body_observation_recorded",
]
