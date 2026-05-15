from __future__ import annotations

FOUNDER_LIVE_MANAGER_EVIDENCE_REQUIRED_FINAL_ACTIONS = ["commit", "correction_applied", "overshoot_note"]
FOUNDER_LIVE_MANAGER_REPAIR_ALLOWED_TOOL_NAMES = [
    "resolve_correction_target",
    "estimate_nutrition",
    "compare_against_budget",
    "body.record_observation",
]
FOUNDER_LIVE_MANAGER_ALLOWED_INTENT_TYPES = [
    "complete_onboarding",
    "answer_remaining_budget",
    "onboarding_required",
    "manager_unavailable",
    "answer_query",
    "log_meal",
    "correct_meal",
    "body_observation",
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
    "record_observation",
]
FOUNDER_LIVE_MANAGER_CALL_TOOLS_FINAL_ACTIONS = [
    "commit",
    "correction_applied",
    "overshoot_note",
    "record_observation",
]
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

__all__ = [
    "FOUNDER_LIVE_MANAGER_ALLOWED_FINAL_ACTIONS",
    "FOUNDER_LIVE_MANAGER_ALLOWED_INTENT_TYPES",
    "FOUNDER_LIVE_MANAGER_CALL_TOOLS_FINAL_ACTIONS",
    "FOUNDER_LIVE_MANAGER_EVIDENCE_REQUIRED_FINAL_ACTIONS",
    "FOUNDER_LIVE_MANAGER_FOLLOWUP_QUESTION_REQUIRED_POSTURES",
    "FOUNDER_LIVE_MANAGER_INTENT_TYPE_BY_SEMANTIC_INTENT",
    "FOUNDER_LIVE_MANAGER_REPAIR_ALLOWED_TOOL_NAMES",
    "FOUNDER_LIVE_MANAGER_RESPONSE_ONLY_FINAL_ACTIONS",
]
