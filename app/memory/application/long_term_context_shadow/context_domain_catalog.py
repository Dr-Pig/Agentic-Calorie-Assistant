from __future__ import annotations

from typing import Any


def _context_domain_catalog() -> list[dict[str, Any]]:
    return (
        _context_domain_group_1()
        + _context_domain_group_2()
        + _context_domain_group_3()
        + _context_domain_group_4()
    )


def _context_domain_group_1() -> list[dict[str, Any]]:
    return [
        {
            "context_domain_id": "food_preference_context",
            "candidate_types": ["food_preference", "pattern"],
            "truth_owner": "memory_derived_from_meal_thread_history",
            "primary_consumers": ["recommendation", "intake_clarification"],
            "risk_if_wrong": "Could overfit ranking or intake defaults to weak evidence.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "negative_preference_context",
            "candidate_types": ["negative_preference"],
            "truth_owner": "human_confirmed_or_reviewed_memory",
            "primary_consumers": ["recommendation", "proactive"],
            "risk_if_wrong": "Could suppress foods or suggestions the user would accept.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "temporary_preference_context",
            "candidate_types": ["temporary_preference"],
            "truth_owner": "time_bounded_reviewed_memory",
            "primary_consumers": ["recommendation", "chat_context", "proactive"],
            "risk_if_wrong": "Could keep expired short-term constraints alive.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "golden_order_context",
            "candidate_types": ["golden_order"],
            "truth_owner": "materialized_view_from_meal_thread_history",
            "primary_consumers": ["recommendation", "intake_clarification"],
            "risk_if_wrong": "Could mistake repeated historical orders for desired defaults.",
            "runtime_injection_allowed": False,
        },
    ]


def _context_domain_group_2() -> list[dict[str, Any]]:
    return [
        {
            "context_domain_id": "user_language_semantic_alias_context",
            "candidate_types": ["user_language_pattern"],
            "truth_owner": "reviewed_language_observation",
            "primary_consumers": [
                "intake_clarification",
                "chat_context",
                "recommendation",
            ],
            "risk_if_wrong": "Could misread personal phrases such as small, normal, or messy eating.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "intake_estimation_bias_context",
            "candidate_types": ["intake_estimation_bias"],
            "truth_owner": "calibration_review_context",
            "primary_consumers": [
                "calibration",
                "nutrition_clarify_priority",
                "intake_risk_tagging",
            ],
            "risk_if_wrong": "Could misattribute calorie mismatch to user logging behavior.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "app_usage_style_context",
            "candidate_types": ["app_usage_style"],
            "truth_owner": "reviewed_usage_pattern",
            "primary_consumers": [
                "chat_context",
                "proactive",
                "cross_surface_experience",
            ],
            "risk_if_wrong": "Could personalize app behavior before the pattern is real.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "interaction_preference_context",
            "candidate_types": ["interaction_preference"],
            "truth_owner": "reviewed_interaction_pattern",
            "primary_consumers": ["chat_context", "proactive", "response_generation"],
            "risk_if_wrong": "Could make answers too terse, too verbose, or ask poorly timed questions.",
            "runtime_injection_allowed": False,
        },
    ]


def _context_domain_group_3() -> list[dict[str, Any]]:
    return [
        {
            "context_domain_id": "logging_adherence_context",
            "candidate_types": ["logging_adherence_pattern", "pattern"],
            "truth_owner": "deterministic_history_aggregation",
            "primary_consumers": ["calibration", "proactive", "rescue_later"],
            "risk_if_wrong": "Could distort confidence in calibration or reminder timing.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "conversation_recall_context",
            "candidate_types": ["conversation_recall_context"],
            "truth_owner": "summary_first_conversation_archive",
            "primary_consumers": [
                "chat_context",
                "intake_clarification",
                "recommendation",
                "calibration",
            ],
            "risk_if_wrong": "Could pull stale prior conversation into the current turn.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "proactive_suppression_context",
            "candidate_types": ["interaction_preference", "app_usage_style"],
            "truth_owner": "future_reviewed_suppression_memory",
            "primary_consumers": ["proactive"],
            "risk_if_wrong": "Could send unwanted nudges or suppress useful ones.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "rescue_history_context",
            "candidate_types": ["logging_adherence_pattern", "pattern"],
            "truth_owner": "proposal_and_budget_history_summary",
            "primary_consumers": ["rescue_later", "calibration"],
            "risk_if_wrong": "Could overstate short-term recovery viability.",
            "runtime_injection_allowed": False,
        },
    ]


def _context_domain_group_4() -> list[dict[str, Any]]:
    return [
        {
            "context_domain_id": "calibration_quality_context",
            "candidate_types": ["intake_estimation_bias", "logging_adherence_pattern"],
            "truth_owner": "calibration_model_context_summary",
            "primary_consumers": ["calibration", "intake_clarification"],
            "risk_if_wrong": "Could reduce trust in body/budget calibration decisions.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "cross_surface_context",
            "candidate_types": [
                "app_usage_style",
                "conversation_recall_context",
                "interaction_preference",
            ],
            "truth_owner": "runtime_surface_context_summary",
            "primary_consumers": ["cross_surface_experience", "chat_context"],
            "risk_if_wrong": "Could make chat, UI, and quick actions feel inconsistent.",
            "runtime_injection_allowed": False,
        },
    ]
