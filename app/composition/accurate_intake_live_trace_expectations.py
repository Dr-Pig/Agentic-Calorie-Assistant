from __future__ import annotations

from typing import Any


SUPPORTED_CASE_ID = "explicit_item_removal_seeded"


def grade_live_trace_expectations(case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case.get("case_id") or "")
    if case_id != SUPPORTED_CASE_ID:
        return {
            "expectation_id": "not_applicable",
            "case_id": case_id,
            "required_status": "not_applicable",
            "ideal_target_status": "not_applicable",
            "checks": [],
            "ideal_targets": [],
        }

    invocations = [_dict(item) for item in _list(case.get("provider_invocations"))]
    scopes = [str(item.get("manager_loop_scope") or "") for item in invocations]
    tool_names = _tool_names(case)
    final_actions = _final_actions(case)
    required_checks = [
        _check("entry_scope_not_repeated", scopes.count("turn_entry_or_read_only") <= 1, {"scopes": scopes}),
        _check("intake_execution_scope_present", "intake_execution" in scopes, {"scopes": scopes}),
        _check("provider_invocation_count_at_most_3", len(invocations) <= 3, {"count": len(invocations)}),
        _check("resolve_target_used", "resolve_correction_target" in tool_names, {"tool_names": tool_names}),
        _check("estimate_nutrition_not_used_for_removal", "estimate_nutrition" not in tool_names, {"tool_names": tool_names}),
        _check("correction_final_present", "correction_applied" in final_actions, {"final_actions": final_actions}),
    ]
    ideal_targets = [_entry_without_intake_tool_call_target(invocations)]
    return {
        "expectation_id": "explicit_item_removal_seeded.trace.v1",
        "case_id": case_id,
        "required_status": _aggregate(required_checks),
        "ideal_target_status": _aggregate(ideal_targets),
        "checks": required_checks,
        "ideal_targets": ideal_targets,
    }


def _entry_without_intake_tool_call_target(invocations: list[dict[str, Any]]) -> dict[str, Any]:
    entry_invocations = [
        item for item in invocations if str(item.get("manager_loop_scope") or "") == "turn_entry_or_read_only"
    ]
    if not entry_invocations:
        return _target("entry_routes_without_intake_tool_call", "not_checked", {"reason": "entry_scope_missing"})
    parsed = _dict(_dict(entry_invocations[0].get("provider_trace")).get("parsed_object"))
    if not parsed:
        return _target("entry_routes_without_intake_tool_call", "not_checked", {"reason": "parsed_object_missing"})
    tools = _tool_names_from_decision(parsed)
    passed = not any(tool in {"estimate_nutrition", "resolve_correction_target", "compare_against_budget"} for tool in tools)
    return _target("entry_routes_without_intake_tool_call", "pass" if passed else "fail", {"entry_tool_names": tools})


def _tool_names(case: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for invocation in _list(case.get("provider_invocations")):
        parsed = _dict(_dict(_dict(invocation).get("provider_trace")).get("parsed_object"))
        names.extend(_tool_names_from_decision(parsed))
    for turn in _list(case.get("turns")):
        for round_item in _list(_dict(turn).get("manager_rounds")):
            names.extend(_tool_names_from_decision(_dict(_dict(round_item).get("decision"))))
    return names


def _final_actions(case: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    for invocation in _list(case.get("provider_invocations")):
        parsed = _dict(_dict(_dict(invocation).get("provider_trace")).get("parsed_object"))
        action = str(parsed.get("final_action") or "")
        if action:
            actions.append(action)
    for turn in _list(case.get("turns")):
        for round_item in _list(_dict(turn).get("manager_rounds")):
            action = str(_dict(_dict(round_item).get("decision")).get("final_action") or "")
            if action:
                actions.append(action)
    return actions


def _tool_names_from_decision(decision: dict[str, Any]) -> list[str]:
    return [
        str(_dict(call).get("name") or _dict(call).get("tool_name") or "")
        for call in _list(decision.get("tool_calls"))
        if str(_dict(call).get("name") or _dict(call).get("tool_name") or "")
    ]


def _check(check_id: str, passed: bool, observed: dict[str, Any]) -> dict[str, Any]:
    return {"check_id": check_id, "status": "pass" if passed else "fail", "observed": observed}


def _target(target_id: str, status: str, observed: dict[str, Any]) -> dict[str, Any]:
    return {"target_id": target_id, "status": status, "observed": observed}


def _aggregate(items: list[dict[str, Any]]) -> str:
    statuses = {str(item.get("status") or "") for item in items}
    if "fail" in statuses:
        return "fail"
    if statuses == {"not_checked"}:
        return "not_checked"
    return "pass"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = ["grade_live_trace_expectations"]
