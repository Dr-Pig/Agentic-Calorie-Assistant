from __future__ import annotations

from collections.abc import Callable
import re
from typing import Any

from app.composition.accurate_intake_trace_expectation_primitives import (
    _aggregate,
    _check,
    _delta,
    _dict,
    _effect,
    _final,
    _final_actions,
    _list,
    _same_truth,
    _target,
    _tools,
    _turn,
    _turn_estimate_commit_check,
    _turn_tools,
    _turns,
    _decision_tools,
)
from app.composition.accurate_intake_call_topology_expectations import call_topology_check
from app.composition.accurate_intake_live_trace_expectation_catalog import EXPECTED_TRACE_BY_CASE_ID


def grade_case_trace_expectation(case: dict[str, Any]) -> dict[str, Any] | None:
    grader = _GRADERS_BY_CASE_ID.get(str(case.get("case_id") or ""))
    return None if grader is None else grader(case)


def _grade_seeded_removal(case: dict[str, Any]) -> dict[str, Any]:
    case_id = "explicit_item_removal_seeded"
    invocations = [_dict(item) for item in _list(case.get("provider_invocations"))]
    scopes = [str(item.get("manager_loop_scope") or "") for item in invocations]
    tool_names = _tools(case)
    checks = [
        _check("entry_scope_not_repeated", scopes.count("turn_entry_or_read_only") <= 1, {"scopes": scopes}),
        _check("intake_execution_scope_present", "intake_execution" in scopes, {"scopes": scopes}),
        _check("provider_invocation_count_at_most_2", len(invocations) <= 2, {"count": len(invocations)}),
        _check("resolve_target_used", "resolve_correction_target" in tool_names, {"tool_names": tool_names}),
        _check("estimate_nutrition_not_used_for_removal", "estimate_nutrition" not in tool_names, {"tool_names": tool_names}),
        _check("correction_final_present", "correction_applied" in _final_actions(case), {"final_actions": _final_actions(case)}),
    ]
    ideal_targets = [_entry_without_intake_tool_call_target(invocations)]
    return _grade(case_id, checks, ideal_targets=ideal_targets)


def _grade_exact_item(case: dict[str, Any]) -> dict[str, Any]:
    case_id = "exact_item_official_label"
    turn = _turn(case, 1)
    tool_names = _tools(case)
    checks = [
        _check("single_turn_only", len(_turns(case)) == 1, {"turn_count": len(_turns(case))}),
        call_topology_check(case_id, case),
        _check("estimate_nutrition_used", "estimate_nutrition" in tool_names, {"tool_names": tool_names}),
        _check("target_resolution_not_used", "resolve_correction_target" not in tool_names, {"tool_names": tool_names}),
        _check("commit_final_present", _final(turn) == "commit", {"final_action": _final(turn)}),
        _check("canonical_commit_recorded", _delta(turn).get("canonical_commit") is True, {"state_delta": _delta(turn)}),
    ]
    return _grade(case_id, checks)


def _grade_chicken_rice(case: dict[str, Any]) -> dict[str, Any]:
    case_id = "chinese_chicken_rice_correction_removal_debug"
    turn_count = len(_turns(case))
    checks = [
        _check("turn_prefix_or_full_path", 1 <= turn_count <= 4, {"turn_count": turn_count}),
        call_topology_check(case_id, case),
    ]
    if turn_count >= 1:
        checks.append(_turn_estimate_commit_check(case, 1))
    if turn_count >= 2:
        turn = _turn(case, 2)
        tools = _turn_tools(turn)
        checks.append(
            _check(
                "turn2_resolves_estimates_and_supersedes",
                _final(turn) == "correction_applied"
                and {"resolve_correction_target", "estimate_nutrition"}.issubset(set(tools))
                and _delta(turn).get("old_version_superseded") is True,
                {"final_action": _final(turn), "tool_names": tools, "state_delta": _delta(turn)},
            )
        )
    if turn_count >= 3:
        turn = _turn(case, 3)
        tools = _turn_tools(turn)
        checks.append(
            _check(
                "turn3_removes_without_nutrition_estimate",
                _final(turn) == "correction_applied"
                and "resolve_correction_target" in tools
                and "estimate_nutrition" not in tools
                and _delta(turn).get("old_version_superseded") is True,
                {"final_action": _final(turn), "tool_names": tools, "state_delta": _delta(turn)},
            )
        )
    checks.append(_check("same_truth_pass", _same_truth(case) == "pass", {"same_truth_status": _same_truth(case)}))
    if turn_count >= 4:
        turn = _turn(case, 4)
        checks.append(
            _check(
                "turn4_read_only_answer",
                _effect(turn) == "answer_only" and _delta(turn).get("canonical_commit") is False,
                {"workflow_effect": _effect(turn), "state_delta": _delta(turn)},
            )
        )
    return _grade(case_id, checks)


def _grade_bubble_tea(case: dict[str, Any]) -> dict[str, Any]:
    case_id = "bubble_milk_tea_refinement"
    turn2 = _turn(case, 2)
    turn2_final_action = _final(turn2)
    checks = [
        _check("two_turn_refinement", len(_turns(case)) == 2, {"turn_count": len(_turns(case))}),
        call_topology_check(case_id, case),
        _turn_estimate_commit_check(case, 1, no_supersede=True),
        _check(
            "turn2_attaches_to_committed_thread",
            turn2_final_action in {"commit", "correction_applied"} and "estimate_nutrition" in _turn_tools(turn2),
            {"final_action": turn2_final_action, "tool_names": _turn_tools(turn2)},
        ),
        _check("turn2_supersedes_old_version", _delta(turn2).get("old_version_superseded") is True, {"state_delta": _delta(turn2)}),
        _check("same_truth_pass", _same_truth(case) == "pass", {"same_truth_status": _same_truth(case)}),
    ]
    return _grade(case_id, checks)


def _grade_luwei(case: dict[str, Any]) -> dict[str, Any]:
    case_id = "luwei_bare_to_listed_basket"
    turn1 = _turn(case, 1)
    turn2 = _turn(case, 2)
    checks = [
        _check("two_turn_blocking_clarify", len(_turns(case)) == 2, {"turn_count": len(_turns(case))}),
        call_topology_check(case_id, case),
        _check("turn1_asks_followup", _final(turn1) == "ask_followup", {"final_action": _final(turn1)}),
        _check(
            "turn1_draft_saved_without_commit",
            _delta(turn1).get("draft_saved") is True and _delta(turn1).get("canonical_commit") is False,
            {"state_delta": _delta(turn1)},
        ),
        _check("turn2_estimates_after_listed_basket", "estimate_nutrition" in _turn_tools(turn2), {"tool_names": _turn_tools(turn2)}),
        _check(
            "turn2_commits_after_clarification",
            _final(turn2) == "commit" and _delta(turn2).get("canonical_commit") is True,
            {"final_action": _final(turn2), "state_delta": _delta(turn2)},
        ),
    ]
    return _grade(case_id, checks)


def _grade_today_query(case: dict[str, Any]) -> dict[str, Any]:
    return _grade_read_only_query("today_consumed_query_only", case)


def _grade_no_plan_query(case: dict[str, Any]) -> dict[str, Any]:
    turn = _turn(case, 1)
    remaining = _dict(turn.get("remaining_budget"))
    reply_texts = _case_reply_texts(case)
    zero_claims = [text for text in reply_texts if _contains_missing_budget_zero_claim(text)]
    coach_message = str(turn.get("coach_message") or "")
    checks = _read_only_checks("no_plan_consumed_without_budget_target", case)
    checks.append(
        _check(
            "no_plan_target_or_remaining_not_invented",
            remaining.get("daily_target_kcal") is None and remaining.get("remaining_kcal") is None,
            {"remaining_budget": remaining},
        )
    )
    checks.append(
        _check(
            "no_plan_reply_does_not_claim_zero_budget_or_remaining",
            not zero_claims,
            {"reply_texts_checked": reply_texts, "forbidden_zero_claims": zero_claims},
        )
    )
    checks.append(
        _check(
            "no_plan_coach_message_is_user_facing_degraded_reply",
            _looks_like_degraded_no_plan_reply(coach_message),
            {"coach_message": coach_message},
        )
    )
    return _grade("no_plan_consumed_without_budget_target", checks)


def _grade_read_only_query(case_id: str, case: dict[str, Any]) -> dict[str, Any]:
    return _grade(case_id, _read_only_checks(case_id, case))


def _read_only_checks(case_id: str, case: dict[str, Any]) -> list[dict[str, Any]]:
    turn = _turn(case, 1)
    return [
        _check("single_turn_only", len(_turns(case)) == 1, {"turn_count": len(_turns(case))}),
        call_topology_check(case_id, case),
        _check("answer_only_workflow", _effect(turn) == "answer_only", {"workflow_effect": _effect(turn)}),
        _check("no_tool_call_needed", _tools(case) == [], {"tool_names": _tools(case)}),
        _check(
            "no_mutation",
            _delta(turn).get("canonical_commit") is False and _delta(turn).get("ledger_updated") is False,
            {"state_delta": _delta(turn)},
        ),
    ]


_GRADERS_BY_CASE_ID: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "explicit_item_removal_seeded": _grade_seeded_removal,
    "exact_item_official_label": _grade_exact_item,
    "chinese_chicken_rice_correction_removal_debug": _grade_chicken_rice,
    "bubble_milk_tea_refinement": _grade_bubble_tea,
    "luwei_bare_to_listed_basket": _grade_luwei,
    "today_consumed_query_only": _grade_today_query,
    "no_plan_consumed_without_budget_target": _grade_no_plan_query,
}


def _grade(case_id: str, checks: list[dict[str, Any]], *, ideal_targets: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    ideal_targets = list(ideal_targets or [])
    return {
        "expectation_id": f"{case_id}.trace.v1",
        "case_id": case_id,
        "required_status": _aggregate(checks),
        "ideal_target_status": _aggregate(ideal_targets) if ideal_targets else "pass",
        "expected_trace": EXPECTED_TRACE_BY_CASE_ID[case_id],
        "checks": checks,
        "ideal_targets": ideal_targets,
    }


def _entry_without_intake_tool_call_target(invocations: list[dict[str, Any]]) -> dict[str, Any]:
    entries = [item for item in invocations if str(item.get("manager_loop_scope") or "") == "turn_entry_or_read_only"]
    if not entries:
        return _target("entry_routes_without_intake_tool_call", "not_checked", {"reason": "entry_scope_missing"})
    parsed = _dict(_dict(entries[0].get("provider_trace")).get("parsed_object"))
    tools = _decision_tools(parsed)
    bad = {"estimate_nutrition", "resolve_correction_target", "compare_against_budget"}
    return _target("entry_routes_without_intake_tool_call", "fail" if bad.intersection(tools) else "pass", {"entry_tool_names": tools})


_CJK_MISSING_BUDGET_ZERO_RE = re.compile(
    r"(預算|目標|剩餘|還剩|可用)[^。！？!?，,；;:\n]{0,16}(0|零)\s*(卡路里|大卡|卡|kcal)?",
    re.IGNORECASE,
)
_EN_MISSING_BUDGET_ZERO_RE = re.compile(
    r"\b(budget|target|remaining|left|available)\b[^.\n,;:!?]{0,24}\b0\b"
    r"|\b0\b[^.\n,;:!?]{0,24}\b(budget|target|remaining|left|available)\b",
    re.IGNORECASE,
)


def _case_reply_texts(case: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for turn in _turns(case):
        _append_reply_text(texts, turn.get("coach_message"))
        for round_item in _list(turn.get("manager_rounds")):
            decision = _dict(_dict(round_item).get("decision"))
            _append_reply_text(texts, _dict(decision.get("answer_contract")).get("reply_text"))
    for invocation in _list(case.get("provider_invocations")):
        parsed = _dict(_dict(_dict(invocation).get("provider_trace")).get("parsed_object"))
        _append_reply_text(texts, _dict(parsed.get("answer_contract")).get("reply_text"))
    return texts


def _append_reply_text(texts: list[str], value: Any) -> None:
    if isinstance(value, str) and value.strip():
        texts.append(value.strip())


def _contains_missing_budget_zero_claim(text: str) -> bool:
    return bool(_CJK_MISSING_BUDGET_ZERO_RE.search(text) or _EN_MISSING_BUDGET_ZERO_RE.search(text))


def _looks_like_degraded_no_plan_reply(text: str) -> bool:
    if not text.strip() or "Onboarding is required" in text:
        return False
    return "設定" in text and ("剩餘" in text or "熱量" in text)


__all__ = ["grade_case_trace_expectation"]
