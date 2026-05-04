from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _contextual_friction_budget_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="contextual_friction_budget_shadow_eval",
        fixture=fixture,
        extra={
            "intake_commit_requested": False,
            "response_generated": False,
            "default_strategy": "estimate_then_one_targeted_followup_if_needed",
            "max_followup_questions_shadow": 1,
            "reversible_default_required": True,
            "friction_decisions": _friction_decisions(candidates),
            "measurement_plan": [
                "time_to_first_value",
                "followup_turn_count",
                "user_correction_rate",
                "dismissal_or_abandonment_rate",
            ],
        },
    )


def _friction_decisions(
    candidates: list[LongTermContextCandidate],
) -> list[dict[str, Any]]:
    return [
        _decision(
            "user_language_pattern",
            candidates,
            {"user_language_pattern"},
            "use_reversible_default_with_short_confirmation",
        ),
        _decision(
            "intake_estimation_bias",
            candidates,
            {"intake_estimation_bias"},
            "ask_one_targeted_followup",
        ),
        _decision(
            "interaction_preference",
            candidates,
            {"interaction_preference"},
            "short_direct_answer",
        ),
        _decision(
            "app_usage_style",
            candidates,
            {"app_usage_style"},
            "stay_in_current_chat_surface",
        ),
    ]


def _decision(
    context_domain: str,
    candidates: list[LongTermContextCandidate],
    candidate_types: set[str],
    recommended_interaction: str,
) -> dict[str, Any]:
    source_ids = [
        candidate.candidate_id
        for candidate in candidates
        if candidate.candidate_type in candidate_types
    ]
    return {
        "context_domain": context_domain,
        "source_candidate_ids": source_ids,
        "recommended_interaction": recommended_interaction,
        "user_effort_goal": "reduce_repeated_questions_without_hiding_uncertainty",
        "followup_budget": 1,
        "reversible_default_allowed": context_domain != "intake_estimation_bias",
        "runtime_effect_allowed": False,
    }


__all__ = ["_contextual_friction_budget_shadow_artifact"]
