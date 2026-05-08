from __future__ import annotations

from typing import Any


def _tools(case: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for invocation in _list(case.get("provider_invocations")):
        names.extend(_decision_tools(_dict(_dict(_dict(invocation).get("provider_trace")).get("parsed_object"))))
    for turn in _turns(case):
        names.extend(_turn_tools(turn))
    return names


def _turn_tools(turn: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for round_item in _list(turn.get("manager_rounds")):
        names.extend(_decision_tools(_dict(_dict(round_item).get("decision"))))
    return names


def _decision_tools(decision: dict[str, Any]) -> list[str]:
    return [
        name
        for call in _list(decision.get("tool_calls"))
        if (name := str(_dict(call).get("name") or _dict(call).get("tool_name") or ""))
    ]


def _final_actions(case: dict[str, Any]) -> list[str]:
    actions = [
        action
        for invocation in _list(case.get("provider_invocations"))
        if (
            action := str(
                _dict(_dict(_dict(invocation).get("provider_trace")).get("parsed_object")).get("final_action") or ""
            )
        )
    ]
    for turn in _turns(case):
        actions.extend(
            str(_dict(_dict(round_item).get("decision")).get("final_action") or "")
            for round_item in _list(turn.get("manager_rounds"))
        )
    return [action for action in actions if action]


def _turns(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [_dict(item) for item in _list(case.get("turns"))]


def _turn(case: dict[str, Any], number: int) -> dict[str, Any]:
    return next((turn for turn in _turns(case) if int(turn.get("turn") or 0) == number), {})


def _turn_estimate_commit_check(case: dict[str, Any], turn_number: int, *, no_supersede: bool = False) -> dict[str, Any]:
    turn = _turn(case, turn_number)
    passed = _final(turn) == "commit" and "estimate_nutrition" in _turn_tools(turn) and _delta(turn).get("canonical_commit") is True
    if no_supersede:
        passed = passed and _delta(turn).get("old_version_superseded") is False
    return _check(
        f"turn{turn_number}_estimate_and_commit",
        passed,
        {"final_action": _final(turn), "tool_names": _turn_tools(turn), "state_delta": _delta(turn)},
    )


def _final(turn: dict[str, Any]) -> str:
    return str(turn.get("manager_final_action") or "")


def _effect(turn: dict[str, Any]) -> str:
    return str(turn.get("workflow_effect") or "")


def _delta(turn: dict[str, Any]) -> dict[str, Any]:
    return _dict(turn.get("state_delta"))


def _same_truth(case: dict[str, Any]) -> str:
    return str(_dict(_dict(_dict(case.get("debug_surface")).get("model")).get("same_truth")).get("status") or "")


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
