from __future__ import annotations

from typing import Any

FOUNDER_LIVE_MANAGER_EVIDENCE_REQUIRED_FINAL_ACTIONS = ["commit", "correction_applied", "overshoot_note"]
FOUNDER_LIVE_MANAGER_REPAIR_ALLOWED_TOOL_NAMES = [
    "resolve_correction_target",
    "estimate_nutrition",
    "compare_against_budget",
]
FOUNDER_LIVE_MANAGER_BODY_OBSERVATION_TOOL_NAMES = ["body.record_observation"]
FOUNDER_LIVE_MANAGER_ALLOWED_INTENT_TYPES = [
    "complete_onboarding",
    "answer_remaining_budget",
    "onboarding_required",
    "manager_unavailable",
    "answer_query",
    "log_meal",
    "correct_meal",
]
FOUNDER_LIVE_MANAGER_ENTRY_ALLOWED_INTENT_TYPES = [
    *FOUNDER_LIVE_MANAGER_ALLOWED_INTENT_TYPES,
    "body_observation",
]
FOUNDER_LIVE_MANAGER_BODY_OBSERVATION_ALLOWED_INTENT_TYPES = [
    "body_observation",
    "manager_unavailable",
]
FOUNDER_LIVE_MANAGER_ALLOWED_FINAL_ACTIONS = [
    "commit",
    "ask_followup",
    "correction_applied",
    "overshoot_note",
    "answer_only",
    "no_commit",
    "answer_remaining_budget",
    "onboarding_required",
    "manager_unavailable",
    "complete_onboarding",
]
FOUNDER_LIVE_MANAGER_BODY_OBSERVATION_ALLOWED_FINAL_ACTIONS = [
    "record_observation",
    "answer_only",
    "no_commit",
    "manager_unavailable",
]
FOUNDER_LIVE_MANAGER_CALL_TOOLS_FINAL_ACTIONS = [
    "commit",
    "correction_applied",
    "overshoot_note",
]
FOUNDER_LIVE_MANAGER_BODY_OBSERVATION_CALL_TOOLS_FINAL_ACTIONS = ["record_observation"]
FOUNDER_LIVE_MANAGER_RESPONSE_ONLY_FINAL_ACTIONS = [
    "ask_followup",
    "answer_only",
    "no_commit",
    "answer_remaining_budget",
    "onboarding_required",
    "manager_unavailable",
    "complete_onboarding",
]
FOUNDER_LIVE_MANAGER_FOLLOWUP_QUESTION_REQUIRED_POSTURES = {
    "refinement_not_commit_gate",
    "size_clarification",
}
FOUNDER_LIVE_MANAGER_INTENT_TYPE_BY_SEMANTIC_INTENT = {
    "complete_onboarding": "complete_onboarding",
    "answer_remaining_budget": "answer_remaining_budget",
    "answer_query": "answer_query",
    "log_meal": "log_meal",
    "correct_meal": "correct_meal",
    "body_observation": "body_observation",
}


def _manager_loop_scope(constraints: dict[str, Any] | None) -> str:
    if not isinstance(constraints, dict):
        return ""
    return str(constraints.get("manager_loop_scope") or "")


def founder_live_manager_allowed_intent_types_for_constraints(
    constraints: dict[str, Any] | None,
) -> list[str]:
    scope = _manager_loop_scope(constraints)
    if scope == "turn_entry_or_read_only":
        return list(FOUNDER_LIVE_MANAGER_ENTRY_ALLOWED_INTENT_TYPES)
    if scope == "body_observation":
        return list(FOUNDER_LIVE_MANAGER_BODY_OBSERVATION_ALLOWED_INTENT_TYPES)
    return list(FOUNDER_LIVE_MANAGER_ALLOWED_INTENT_TYPES)


def founder_live_manager_allowed_final_actions_for_constraints(
    constraints: dict[str, Any] | None,
) -> list[str]:
    if _manager_loop_scope(constraints) == "body_observation":
        return list(FOUNDER_LIVE_MANAGER_BODY_OBSERVATION_ALLOWED_FINAL_ACTIONS)
    return list(FOUNDER_LIVE_MANAGER_ALLOWED_FINAL_ACTIONS)


def founder_live_manager_call_tools_final_actions_for_constraints(
    constraints: dict[str, Any] | None,
) -> list[str]:
    if _manager_loop_scope(constraints) == "body_observation":
        return list(FOUNDER_LIVE_MANAGER_BODY_OBSERVATION_CALL_TOOLS_FINAL_ACTIONS)
    return list(FOUNDER_LIVE_MANAGER_CALL_TOOLS_FINAL_ACTIONS)


def founder_live_manager_tool_names_for_constraints(
    constraints: dict[str, Any] | None,
) -> list[str]:
    if _manager_loop_scope(constraints) == "body_observation":
        return list(FOUNDER_LIVE_MANAGER_BODY_OBSERVATION_TOOL_NAMES)
    return list(FOUNDER_LIVE_MANAGER_REPAIR_ALLOWED_TOOL_NAMES)


def founder_live_manager_response_only_final_actions_for_constraints(
    constraints: dict[str, Any] | None,
) -> list[str]:
    if _manager_loop_scope(constraints) == "body_observation":
        return ["answer_only", "no_commit", "manager_unavailable"]
    return list(FOUNDER_LIVE_MANAGER_RESPONSE_ONLY_FINAL_ACTIONS)


__all__ = [
    "FOUNDER_LIVE_MANAGER_ALLOWED_FINAL_ACTIONS",
    "FOUNDER_LIVE_MANAGER_ALLOWED_INTENT_TYPES",
    "FOUNDER_LIVE_MANAGER_BODY_OBSERVATION_ALLOWED_FINAL_ACTIONS",
    "FOUNDER_LIVE_MANAGER_BODY_OBSERVATION_ALLOWED_INTENT_TYPES",
    "FOUNDER_LIVE_MANAGER_BODY_OBSERVATION_CALL_TOOLS_FINAL_ACTIONS",
    "FOUNDER_LIVE_MANAGER_BODY_OBSERVATION_TOOL_NAMES",
    "FOUNDER_LIVE_MANAGER_CALL_TOOLS_FINAL_ACTIONS",
    "FOUNDER_LIVE_MANAGER_EVIDENCE_REQUIRED_FINAL_ACTIONS",
    "FOUNDER_LIVE_MANAGER_ENTRY_ALLOWED_INTENT_TYPES",
    "FOUNDER_LIVE_MANAGER_FOLLOWUP_QUESTION_REQUIRED_POSTURES",
    "FOUNDER_LIVE_MANAGER_INTENT_TYPE_BY_SEMANTIC_INTENT",
    "FOUNDER_LIVE_MANAGER_REPAIR_ALLOWED_TOOL_NAMES",
    "FOUNDER_LIVE_MANAGER_RESPONSE_ONLY_FINAL_ACTIONS",
    "founder_live_manager_allowed_final_actions_for_constraints",
    "founder_live_manager_allowed_intent_types_for_constraints",
    "founder_live_manager_call_tools_final_actions_for_constraints",
    "founder_live_manager_response_only_final_actions_for_constraints",
    "founder_live_manager_tool_names_for_constraints",
]
