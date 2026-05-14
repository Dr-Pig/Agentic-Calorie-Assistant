from __future__ import annotations

from typing import Any

from app.composition.accurate_intake_trace_expectation_primitives import (
    _check,
    _dict,
    _list,
    _turns,
)


EXPECTED_CALL_TOPOLOGY_BY_CASE_ID = {
    "exact_item_official_label": {1: ["turn_entry_or_read_only", "intake_execution", "intake_execution"]},
    "generic_common_food_range": {1: ["turn_entry_or_read_only", "intake_execution"]},
    "explicit_item_removal_seeded": {1: ["turn_entry_or_read_only", "intake_execution"]},
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
        2: ["turn_entry_or_read_only", "intake_execution", "intake_execution"],
    },
    "teppan_breakfast_explain_refine_dogfood": {
        1: ["turn_entry_or_read_only", "intake_execution"],
        2: ["turn_entry_or_read_only", "intake_execution"],
        3: ["turn_entry_or_read_only"],
    },
    "today_consumed_query_only": {1: ["turn_entry_or_read_only"]},
    "no_plan_consumed_without_budget_target": {1: ["turn_entry_or_read_only"]},
}

ACCEPTED_ALTERNATE_CALL_TOPOLOGY_BY_CASE_ID = {
    "exact_item_official_label": {
        1: [["turn_entry_or_read_only", "intake_execution"]],
    },
    "luwei_bare_to_listed_basket": {
        2: [["turn_entry_or_read_only", "intake_execution"]],
    },
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
    topology_matches = observed_by_turn == expected_by_turn and not unexpected_turns
    if not topology_matches:
        topology_matches = _matches_accepted_alternate(
            case_id=case_id,
            expected_by_turn=expected_by_turn,
            observed_by_turn=observed_by_turn,
            unexpected_turns=unexpected_turns,
        )
    observed = {
        "expected_by_turn": expected_by_turn,
        "observed_by_turn": observed_by_turn,
        "unexpected_turns": unexpected_turns,
    }
    accepted_alternates = ACCEPTED_ALTERNATE_CALL_TOPOLOGY_BY_CASE_ID.get(case_id)
    if accepted_alternates:
        observed["accepted_alternates"] = accepted_alternates
    return _check(
        "call_topology_matches_expected",
        topology_matches,
        observed,
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


def _matches_accepted_alternate(
    *,
    case_id: str,
    expected_by_turn: dict[int, list[str]],
    observed_by_turn: dict[int, list[str]],
    unexpected_turns: list[int],
) -> bool:
    if unexpected_turns:
        return False
    alternates = ACCEPTED_ALTERNATE_CALL_TOPOLOGY_BY_CASE_ID.get(case_id, {})
    if not alternates:
        return False
    if set(observed_by_turn) != set(expected_by_turn):
        return False
    for turn, expected in expected_by_turn.items():
        observed = observed_by_turn.get(turn)
        if observed == expected:
            continue
        if observed not in alternates.get(turn, []):
            return False
    return True


__all__ = [
    "ACCEPTED_ALTERNATE_CALL_TOPOLOGY_BY_CASE_ID",
    "EXPECTED_CALL_TOPOLOGY_BY_CASE_ID",
    "call_topology_check",
]
