from __future__ import annotations

from typing import Any

from app.composition.accurate_intake_trace_expectation_primitives import (
    _check,
    _dict,
    _list,
    _turns,
)


EXPECTED_CALL_TOPOLOGY_BY_CASE_ID = {
    "exact_item_official_label": {1: ["turn_entry_or_read_only", "intake_execution"]},
    "chinese_chicken_rice_correction_removal_debug": {
        1: ["turn_entry_or_read_only", "intake_execution"],
        2: ["turn_entry_or_read_only", "intake_execution"],
        3: ["turn_entry_or_read_only", "intake_execution"],
        4: ["turn_entry_or_read_only"],
    },
    "bubble_milk_tea_refinement": {
        1: ["turn_entry_or_read_only", "intake_execution"],
        2: ["turn_entry_or_read_only", "intake_execution"],
    },
    "luwei_bare_to_listed_basket": {
        1: ["turn_entry_or_read_only", "intake_execution"],
        2: ["turn_entry_or_read_only", "intake_execution"],
    },
    "today_consumed_query_only": {1: ["turn_entry_or_read_only"]},
    "no_plan_consumed_without_budget_target": {1: ["turn_entry_or_read_only"]},
}


def call_topology_check(case_id: str, case: dict[str, Any]) -> dict[str, Any]:
    expected_all = EXPECTED_CALL_TOPOLOGY_BY_CASE_ID.get(case_id, {})
    executed_turns = [
        turn
        for turn in (_int_or_none(item.get("turn")) for item in _turns(case))
        if turn is not None
    ]
    expected_by_turn = {
        turn: list(expected_all[turn])
        for turn in executed_turns
        if turn in expected_all
    }
    observed_by_turn: dict[int, list[str]] = {}
    for invocation in [_dict(item) for item in _list(case.get("provider_invocations"))]:
        turn = _int_or_none(invocation.get("diagnostic_turn"))
        scope = str(invocation.get("manager_loop_scope") or "")
        if turn is None or not scope:
            continue
        observed_by_turn.setdefault(turn, []).append(scope)
    unexpected_turns = sorted(turn for turn in observed_by_turn if turn not in expected_by_turn)
    return _check(
        "call_topology_matches_expected",
        observed_by_turn == expected_by_turn and not unexpected_turns,
        {
            "expected_by_turn": expected_by_turn,
            "observed_by_turn": observed_by_turn,
            "unexpected_turns": unexpected_turns,
        },
    )


def _int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped)
        except ValueError:
            return None
    return None


__all__ = ["EXPECTED_CALL_TOPOLOGY_BY_CASE_ID", "call_topology_check"]
