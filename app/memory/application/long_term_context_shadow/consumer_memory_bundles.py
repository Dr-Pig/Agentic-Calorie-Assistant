from __future__ import annotations

from typing import Any

from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def consumer_memory_bundles(
    candidates: list[LongTermContextCandidate],
) -> dict[str, dict[str, Any]]:
    return {
        "recommendation": _recommendation_bundle(candidates),
        "proactive": _proactive_bundle(candidates),
        "calibration": _calibration_bundle(candidates),
        "rescue_later": _rescue_bundle(candidates),
    }


def _recommendation_bundle(
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    return {
        "consumer_priority": 1,
        "required_memory_domains": [
            "preference_profile_summary",
            "golden_order_summary",
            "negative_preference_memory",
            "temporary_preference_memory",
            "store_familiarity",
            "calibration_quality_context",
        ],
        "hard_guards": [
            "confirmed_or_reviewed_negative_preference",
            "budget_fit",
            "temporary_preference_validity",
        ],
        "ranking_memory_candidate_ids": _candidate_ids(
            candidates, {"food_preference", "golden_order", "temporary_preference"}
        ),
        "blocking_memory_candidate_ids": _candidate_ids(
            candidates, {"negative_preference"}
        ),
        "soft_signal_candidate_ids": _candidate_ids(
            candidates,
            {"intake_estimation_bias", "logging_adherence_pattern", "pattern"},
        ),
        "runtime_serving_allowed": False,
        "recommendation_served": False,
        "missing_runtime_dependencies": [
            "recommendation_context_result_contract",
            "candidate_spec_generation_runtime",
            "ranking_and_synthesis_runtime",
            "user_visible_memory_review_surface",
        ],
        "runtime_effect_allowed": False,
    }


def _proactive_bundle(candidates: list[LongTermContextCandidate]) -> dict[str, Any]:
    return {
        "consumer_priority": 4,
        "required_memory_domains": [
            "suppression_summary",
            "app_usage_style_memory",
            "interaction_preference_memory",
            "logging_adherence_memory",
            "recommendation_memory_quality",
        ],
        "hard_guards": [
            "quiet_hours",
            "cooldown",
            "recent_send_cap",
            "suppression_memory",
            "minimum_recommendation_context_quality",
        ],
        "blocking_memory_candidate_ids": _candidate_ids(
            candidates,
            {"app_usage_style", "interaction_preference", "negative_preference"},
        ),
        "timing_memory_candidate_ids": _candidate_ids(
            candidates, {"logging_adherence_pattern", "pattern"}
        ),
        "surface_policy": "no_send_shadow_only",
        "scheduler_activation_allowed": False,
        "runtime_serving_allowed": False,
        "runtime_effect_allowed": False,
    }


def _calibration_bundle(candidates: list[LongTermContextCandidate]) -> dict[str, Any]:
    return {
        "consumer_priority": 3,
        "required_memory_domains": [
            "intake_completeness_summary",
            "adherence_summary",
            "calibration_history_summary",
            "intake_estimation_bias_memory",
        ],
        "hard_guards": [
            "observation_quality_gate",
            "intake_quality_gate",
            "trend_window_gate",
        ],
        "attribution_memory_candidate_ids": _candidate_ids(
            candidates,
            {"intake_estimation_bias", "logging_adherence_pattern", "pattern"},
        ),
        "controlled_effects_allowed_later": [
            "clarify_priority",
            "risk_tagging",
            "estimate_conservatism_posture",
        ],
        "math_mutation_allowed": False,
        "body_plan_mutated": False,
        "day_budget_mutated": False,
        "runtime_effect_allowed": False,
    }


def _rescue_bundle(candidates: list[LongTermContextCandidate]) -> dict[str, Any]:
    return {
        "consumer_priority": 5,
        "required_memory_domains": [
            "rescue_history_summary",
            "adherence_summary",
            "recent_overshoot_pattern",
            "interaction_preference_memory",
        ],
        "hard_guards": [
            "current_budget_view_required",
            "safety_floor_required",
            "open_proposal_dedupe",
            "recovery_viability_gate",
        ],
        "viability_memory_candidate_ids": _candidate_ids(
            candidates,
            {"logging_adherence_pattern", "pattern", "intake_estimation_bias"},
        ),
        "presentation_memory_candidate_ids": _candidate_ids(
            candidates, {"interaction_preference"}
        ),
        "proposal_commit_allowed": False,
        "budget_mutation_requested": False,
        "runtime_effect_allowed": False,
    }


def _candidate_ids(
    candidates: list[LongTermContextCandidate], candidate_types: set[str]
) -> list[str]:
    return sorted(
        candidate.candidate_id
        for candidate in candidates
        if candidate.candidate_type in candidate_types
    )


__all__ = ["consumer_memory_bundles"]
