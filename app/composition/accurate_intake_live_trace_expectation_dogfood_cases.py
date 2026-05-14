from __future__ import annotations

import re
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


_INTERNAL_ESTIMATE_LABEL_RE = re.compile(
    r"\b(?:llm(?:_only)?|rough\s+estimate|rough_estimate_without_source|unverified_estimate|confidence_tier)\b",
    re.IGNORECASE,
)
_MACRO_GRAM_CLAIM_RE = re.compile(
    r"(\u86cb\u767d\u8cea|\u78b3\u6c34|\u8102\u80aa|protein|carb|fat)[^\n]{0,16}\d+\s*g",
    re.IGNORECASE,
)


def grade_teppan_breakfast(case: dict[str, Any]) -> dict[str, Any]:
    case_id = "teppan_breakfast_explain_refine_dogfood"
    turn1 = _turn(case, 1)
    turn2 = _turn(case, 2)
    turn3 = _turn(case, 3)
    turn1_delta = _delta(turn1)
    turn2_delta = _delta(turn2)
    turn2_estimation = _dict(turn2.get("estimation_summary"))
    turn2_components = _list(turn2_estimation.get("component_names"))
    turn3_delta = _delta(turn3)
    turn3_basis = _dict(turn3.get("answer_basis"))
    turn2_basis_has_active_meal_evidence = bool(
        turn3_basis.get("meal_thread_id") or str(turn3_basis.get("basis_text") or "").strip()
    )
    turn3_reply_text = str(turn3.get("coach_message") or "")
    checks = [
        _check("three_turn_pending_commit_explain_path", len(_turns(case)) == 3, {"turn_count": len(_turns(case))}),
        call_topology_check(case_id, case),
        _check(
            "turn1_asks_followup_without_commit",
            _effect(turn1) == "ask_followup"
            and _final(turn1) == "ask_followup"
            and turn1_delta.get("canonical_commit") is False
            and turn1_delta.get("ledger_updated") is False
            and turn1_delta.get("draft_saved") is True,
            {"final_action": _final(turn1), "workflow_effect": _effect(turn1), "state_delta": turn1_delta},
        ),
        _check("turn1_no_estimate_tools", _turn_tools(turn1) == [], {"tool_names": _turn_tools(turn1)}),
        _turn_estimate_commit_check(case, 2, no_supersede=True),
        _check(
            "turn2_component_basis_present",
            len(turn2_components) >= 3 and turn2_estimation.get("used_default_fallback_400_macro") is not True,
            {"estimation_summary": turn2_estimation},
        ),
        _check(
            "turn3_answer_only_workflow",
            _effect(turn3) == "answer_only" and _final(turn3) == "answer_only",
            {"workflow_effect": _effect(turn3), "final_action": _final(turn3)},
        ),
        _check("turn3_no_tools", _turn_tools(turn3) == [], {"tool_names": _turn_tools(turn3)}),
        _check(
            "turn3_no_mutation",
            turn3_delta.get("canonical_commit") is False
            and turn3_delta.get("ledger_updated") is False
            and turn3_delta.get("new_meal_version_created") is False
            and turn3_delta.get("old_version_superseded") is False,
            {"state_delta": turn3_delta},
        ),
        _check(
            "turn3_uses_active_meal_basis",
            turn2_basis_has_active_meal_evidence
            and turn3_basis.get("references_active_meal") is True
            and turn3_basis.get("assumption_or_composition_explained") is True,
            {"answer_basis": turn3_basis},
        ),
        _check(
            "turn3_reply_hides_internal_estimate_labels",
            not _INTERNAL_ESTIMATE_LABEL_RE.search(turn3_reply_text),
            {"coach_message": turn3_reply_text},
        ),
        _check(
            "turn3_reply_does_not_show_unsupported_macro_grams",
            not _MACRO_GRAM_CLAIM_RE.search(turn3_reply_text),
            {"coach_message": turn3_reply_text},
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
