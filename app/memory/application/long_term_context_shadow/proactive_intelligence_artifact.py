from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _proactive_intelligence_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    decisions = [
        _trigger_decision(candidate)
        for candidate in candidates
        if _is_proactive_candidate(candidate)
    ]
    return _base_artifact(
        artifact_type="proactive_intelligence_shadow_eval",
        fixture=fixture,
        extra={
            "scheduler_activated": False,
            "channel_send_attempted": False,
            "lowest_autonomy_tier_policy": {
                "default_tier": "observe_only",
                "max_shadow_tier": "suggest",
                "auto_action_allowed": False,
                "ask_approval_before_user_visible_send": True,
            },
            "suppression_policy": {
                "quiet_window_suppresses_push": True,
                "prefer_chat_draft_before_push": True,
                "ui_inbox_surface_required": False,
                "dismiss_snooze_correction_required": True,
                "cooldown_after_dismissal_required": True,
                "low_confidence_requires_more_evidence": True,
            },
            "agentic_product_pattern_basis": [
                "guardrails_before_user_visible_action",
                "session_state_and_scope_before_recall",
                "human_interrupt_or_approval_for_high_impact_action",
                "personalization_control_and_memory_review",
                "lowest_autonomy_tier_that_creates_value",
            ],
            "candidate_trigger_decisions": decisions,
            "decision_rollup": _decision_rollup(decisions),
            "proactive_silence_cases": _proactive_silence_cases(),
            "false_positive_silence_cases": _false_positive_silence_cases(),
        },
    )


def _is_proactive_candidate(candidate: LongTermContextCandidate) -> bool:
    return bool(
        set(candidate.intended_consumers).intersection(
            {"proactive", "proactive_message_style", "rescue_later"}
        )
        or candidate.candidate_type in {"pattern", "logging_adherence_pattern"}
    )


def _trigger_decision(candidate: LongTermContextCandidate) -> dict[str, Any]:
    user_value = _user_value_score(candidate)
    interruption_cost = _interruption_cost_score(candidate)
    annoyance = round(max(0.0, min(1.0, interruption_cost - user_value * 0.35)), 3)
    return {
        "trigger_id": f"proactive-intelligence-{candidate.candidate_id}",
        "source_candidate_id": candidate.candidate_id,
        "trigger_family": _trigger_family(candidate),
        "user_value_score": user_value,
        "interruption_cost_score": interruption_cost,
        "annoyance_risk_score": annoyance,
        "autonomy_tier": _autonomy_tier(user_value, annoyance),
        "recommended_shadow_surface": _recommended_surface(
            candidate, user_value, annoyance
        ),
        "reason": candidate.proposed_memory_text,
        "dismiss_snooze_correction_required": True,
        "proactive_sent": False,
        "runtime_effect_allowed": False,
    }


def _user_value_score(candidate: LongTermContextCandidate) -> float:
    if candidate.candidate_type in {"pattern", "logging_adherence_pattern"}:
        return 0.72
    if candidate.candidate_type == "temporary_preference":
        return 0.68
    if candidate.candidate_type in {"negative_preference", "golden_order"}:
        return 0.58
    if candidate.candidate_type == "app_usage_style":
        return 0.32
    return 0.45


def _interruption_cost_score(candidate: LongTermContextCandidate) -> float:
    if candidate.candidate_type == "app_usage_style":
        return 0.78
    if candidate.candidate_type == "interaction_preference":
        return 0.65
    if candidate.candidate_type in {"pattern", "logging_adherence_pattern"}:
        return 0.45
    return 0.52


def _autonomy_tier(user_value: float, annoyance: float) -> str:
    if user_value >= 0.7 and annoyance < 0.35:
        return "suggest"
    if user_value >= 0.55 and annoyance < 0.55:
        return "draft"
    return "observe_only"


def _recommended_surface(
    candidate: LongTermContextCandidate,
    user_value: float,
    annoyance: float,
) -> str:
    if candidate.candidate_type == "app_usage_style" or annoyance >= 0.55:
        return "silent_observe"
    if user_value >= 0.7:
        return "future_nudge_candidate"
    return "chat_review_candidate"


def _trigger_family(candidate: LongTermContextCandidate) -> str:
    reason = " ".join(candidate.reason_codes)
    if "overshoot" in reason:
        return "overshoot_risk"
    if "weight" in reason:
        return "logging_consistency"
    if candidate.candidate_type in {"app_usage_style", "interaction_preference"}:
        return "interaction_timing"
    return "contextual_assistance"


def _decision_rollup(decisions: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "silent_observe": sum(
            1
            for decision in decisions
            if decision["recommended_shadow_surface"] == "silent_observe"
        ),
        "chat_review_candidate": sum(
            1
            for decision in decisions
            if decision["recommended_shadow_surface"] == "chat_review_candidate"
        ),
        "future_nudge_candidate": sum(
            1
            for decision in decisions
            if decision["recommended_shadow_surface"] == "future_nudge_candidate"
        ),
    }


def _false_positive_silence_cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "late_night_backfill_already_logged",
            "should_stay_silent": True,
            "next_signal_required": "new_unlogged_gap_after_cooldown",
            "runtime_effect_allowed": False,
        },
        {
            "case_id": "low_confidence_preference_signal",
            "should_stay_silent": True,
            "next_signal_required": "more_evidence_or_user_confirmation",
            "runtime_effect_allowed": False,
        },
        {
            "case_id": "recent_user_dismissal",
            "should_stay_silent": True,
            "next_signal_required": "dismissal_cooldown_expired",
            "runtime_effect_allowed": False,
        },
    ]


def _proactive_silence_cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "late_night_backfill_already_logged",
            "why_system_should_stay_silent": (
                "The user may be catching up on logs and another reminder would add "
                "friction without improving evidence quality."
            ),
            "potential_trigger_suppressed": "missed_logging_reminder",
            "user_annoyance_risk": "high_after_recent_logging_activity",
            "future_data_needed": "new_unlogged_gap_after_cooldown",
            "runtime_effect_allowed": False,
        },
        {
            "case_id": "low_confidence_preference_signal",
            "why_system_should_stay_silent": (
                "A weak preference candidate can bias recommendations or reminders "
                "before the user confirms it."
            ),
            "potential_trigger_suppressed": "personalized_food_nudge",
            "user_annoyance_risk": "medium_due_to_unconfirmed_personalization",
            "future_data_needed": "more_evidence_or_user_confirmation",
            "runtime_effect_allowed": False,
        },
        {
            "case_id": "recent_user_dismissal",
            "why_system_should_stay_silent": (
                "Dismissal is an explicit negative timing signal and should suppress "
                "follow-up until the cooldown expires."
            ),
            "potential_trigger_suppressed": "repeat_proactive_prompt",
            "user_annoyance_risk": "high_due_to_repetition",
            "future_data_needed": "dismissal_cooldown_expired_plus_new_signal",
            "runtime_effect_allowed": False,
        },
    ]


__all__ = ["_proactive_intelligence_shadow_artifact"]
