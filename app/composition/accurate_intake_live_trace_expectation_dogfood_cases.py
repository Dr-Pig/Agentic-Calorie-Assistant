from __future__ import annotations

from typing import Any

from app.composition.accurate_intake_call_topology_expectations import call_topology_check
from app.composition.accurate_intake_trace_expectation_primitives import (
    _aggregate,
    _check,
    _delta,
    _dict,
    _effect,
    _final,
    _list,
    _same_truth,
    _turn,
    _turn_estimate_commit_check,
    _turn_tools,
    _turns,
)
from app.composition.accurate_intake_live_trace_expectation_catalog import EXPECTED_TRACE_BY_CASE_ID


def grade_teppan_breakfast(case: dict[str, Any]) -> dict[str, Any]:
    case_id = "teppan_breakfast_explain_refine_dogfood"
    turn2 = _turn(case, 2)
    turn3 = _turn(case, 3)
    turn2_delta = _delta(turn2)
    turn2_basis = _dict(turn2.get("answer_basis"))
    turn3_delta = _delta(turn3)
    turn3_estimation = _dict(turn3.get("estimation_summary"))
    turn3_components = _list(turn3_estimation.get("component_names"))
    checks = [
        _check("three_turn_explain_refine_path", len(_turns(case)) == 3, {"turn_count": len(_turns(case))}),
        call_topology_check(case_id, case),
        _turn_estimate_commit_check(case, 1, no_supersede=True),
        _check(
            "turn2_answer_only_workflow",
            _effect(turn2) == "answer_only" and _final(turn2) == "answer_only",
            {"workflow_effect": _effect(turn2), "final_action": _final(turn2)},
        ),
        _check("turn2_no_tools", _turn_tools(turn2) == [], {"tool_names": _turn_tools(turn2)}),
        _check(
            "turn2_no_mutation",
            turn2_delta.get("canonical_commit") is False
            and turn2_delta.get("ledger_updated") is False
            and turn2_delta.get("new_meal_version_created") is False
            and turn2_delta.get("old_version_superseded") is False,
            {"state_delta": turn2_delta},
        ),
        _check(
            "turn2_uses_active_meal_basis",
            bool(turn2_basis.get("meal_thread_id"))
            and turn2_basis.get("references_active_meal") is True
            and turn2_basis.get("assumption_or_composition_explained") is True,
            {"answer_basis": turn2_basis},
        ),
        _check(
            "turn3_refines_existing_meal",
            _final(turn3) in {"commit", "correction_applied"}
            and "estimate_nutrition" in _turn_tools(turn3)
            and turn3_delta.get("old_version_superseded") is True
            and turn3_delta.get("new_meal_version_created") is True
            and turn3_delta.get("ledger_updated") is True,
            {"final_action": _final(turn3), "tool_names": _turn_tools(turn3), "state_delta": turn3_delta},
        ),
        _check(
            "turn3_component_basis_present",
            len(turn3_components) >= 2 and turn3_estimation.get("used_default_fallback_400_macro") is not True,
            {"estimation_summary": turn3_estimation},
        ),
        _check("same_truth_pass", _same_truth(case) == "pass", {"same_truth_status": _same_truth(case)}),
    ]
    return {
        "expectation_id": f"{case_id}.trace.v1",
        "case_id": case_id,
        "required_status": _aggregate(checks),
        "ideal_target_status": "pass",
        "expected_trace": EXPECTED_TRACE_BY_CASE_ID[case_id],
        "checks": checks,
        "ideal_targets": [],
    }


__all__ = ["grade_teppan_breakfast"]
