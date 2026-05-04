from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.context_domain_catalog import (
    _context_domain_catalog,
)


def _capability_families() -> list[dict[str, Any]]:
    return (
        _capability_family_group_1()
        + _capability_family_group_2()
        + _capability_family_group_3()
    )


def _capability_family_group_1() -> list[dict[str, Any]]:
    return [
        {
            "family_id": "F1",
            "name": "Plan Bootstrap & Fallback",
            "context_domain_ids": [
                "app_usage_style_context",
                "interaction_preference_context",
                "cross_surface_context",
            ],
            "product_objects": ["body_plan", "day_budget_ledger"],
            "memory_role": "Degraded-mode explanation and onboarding preference context only.",
            "runtime_effect_allowed": False,
        },
        {
            "family_id": "F2",
            "name": "Meal Thread Resolution",
            "context_domain_ids": [
                "user_language_semantic_alias_context",
                "intake_estimation_bias_context",
                "food_preference_context",
                "conversation_recall_context",
            ],
            "product_objects": ["meal_thread"],
            "memory_role": "Clarify better without replacing MealThread or FoodDB truth.",
            "runtime_effect_allowed": False,
        },
        {
            "family_id": "F3",
            "name": "Budget & Cross-Surface Sync",
            "context_domain_ids": [
                "logging_adherence_context",
                "cross_surface_context",
                "conversation_recall_context",
            ],
            "product_objects": ["day_budget_ledger", "meal_thread", "body_plan"],
            "memory_role": "Explain and audit sync context; never mutate ledger truth.",
            "runtime_effect_allowed": False,
        },
    ]


def _capability_family_group_2() -> list[dict[str, Any]]:
    return [
        {
            "family_id": "F4",
            "name": "Rescue & Proposal Negotiation",
            "context_domain_ids": [
                "rescue_history_context",
                "logging_adherence_context",
                "interaction_preference_context",
            ],
            "product_objects": ["proposal", "day_budget_ledger"],
            "memory_role": "Future rescue viability and presentation context only.",
            "runtime_effect_allowed": False,
        },
        {
            "family_id": "F5",
            "name": "Body Observation & Calibration",
            "context_domain_ids": [
                "intake_estimation_bias_context",
                "logging_adherence_context",
                "calibration_quality_context",
                "conversation_recall_context",
            ],
            "product_objects": ["body_plan", "proposal"],
            "memory_role": "Support calibration confidence and attribution; do not rewrite plan.",
            "runtime_effect_allowed": False,
        },
        {
            "family_id": "F6",
            "name": "Recommendation & Preference Learning",
            "context_domain_ids": [
                "food_preference_context",
                "negative_preference_context",
                "temporary_preference_context",
                "golden_order_context",
                "menu_highlight_context",
                "conversation_recall_context",
                "calibration_quality_context",
            ],
            "product_objects": [
                "meal_thread",
                "body_plan",
                "day_budget_ledger",
                "preference_memory",
            ],
            "memory_role": "Primary ranking and filtering context after review.",
            "runtime_effect_allowed": False,
        },
    ]


def _capability_family_group_3() -> list[dict[str, Any]]:
    return [
        {
            "family_id": "F7",
            "name": "Proactive Triggering",
            "context_domain_ids": [
                "proactive_suppression_context",
                "app_usage_style_context",
                "interaction_preference_context",
                "logging_adherence_context",
                "food_preference_context",
            ],
            "product_objects": ["proactive_trigger", "proposal"],
            "memory_role": "No-send timing, suppression, and candidate quality context only.",
            "runtime_effect_allowed": False,
        },
        {
            "family_id": "F8",
            "name": "Cross-Channel / Cross-Surface Experience",
            "context_domain_ids": [
                "cross_surface_context",
                "app_usage_style_context",
                "interaction_preference_context",
                "conversation_recall_context",
            ],
            "product_objects": ["meal_thread", "day_budget_ledger", "body_plan"],
            "memory_role": "Keep chat-first personalization coherent across surfaces.",
            "runtime_effect_allowed": False,
        },
    ]


def _consumer_contracts() -> list[dict[str, Any]]:
    return (
        _consumer_contract_group_1()
        + _consumer_contract_group_2()
        + _consumer_contract_group_3()
    )


def _consumer_contract_group_1() -> list[dict[str, Any]]:
    return [
        {
            "consumer_id": "recommendation",
            "uses_context_domains": [
                "food_preference_context",
                "negative_preference_context",
                "temporary_preference_context",
                "golden_order_context",
                "calibration_quality_context",
                "menu_highlight_context",
            ],
            "allowed_use": "shadow ranking/filtering review",
            "forbidden_use": "serving recommendation or committing intake",
        },
        {
            "consumer_id": "intake_clarification",
            "uses_context_domains": [
                "user_language_semantic_alias_context",
                "intake_estimation_bias_context",
                "food_preference_context",
                "menu_highlight_context",
            ],
            "allowed_use": "shadow clarify-priority review",
            "forbidden_use": "rewriting nutrition evidence or FoodDB truth",
        },
        {
            "consumer_id": "chat_context",
            "uses_context_domains": [
                "interaction_preference_context",
                "app_usage_style_context",
                "conversation_recall_context",
                "menu_highlight_context",
            ],
            "allowed_use": "future response-context candidate review",
            "forbidden_use": "automatic prompt injection",
        },
    ]


def _consumer_contract_group_2() -> list[dict[str, Any]]:
    return [
        {
            "consumer_id": "calibration",
            "uses_context_domains": [
                "intake_estimation_bias_context",
                "logging_adherence_context",
                "calibration_quality_context",
            ],
            "allowed_use": "confidence and attribution review",
            "forbidden_use": "direct BodyPlan or DayBudgetLedger mutation",
        },
        {
            "consumer_id": "proactive",
            "uses_context_domains": [
                "proactive_suppression_context",
                "app_usage_style_context",
                "interaction_preference_context",
                "logging_adherence_context",
            ],
            "allowed_use": "no-send simulation",
            "forbidden_use": "scheduler activation or channel send",
        },
        {
            "consumer_id": "rescue_later",
            "uses_context_domains": [
                "rescue_history_context",
                "logging_adherence_context",
                "interaction_preference_context",
            ],
            "allowed_use": "future rescue viability review",
            "forbidden_use": "rescue proposal commit or budget overlay mutation",
        },
    ]


def _consumer_contract_group_3() -> list[dict[str, Any]]:
    return [
        {
            "consumer_id": "cross_surface_experience",
            "uses_context_domains": [
                "cross_surface_context",
                "app_usage_style_context",
                "conversation_recall_context",
            ],
            "allowed_use": "surface consistency review",
            "forbidden_use": "creating parallel UI/channel truth",
        },
    ]


def _candidate_type_to_context_domain() -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for domain in _context_domain_catalog():
        for candidate_type in domain["candidate_types"]:
            mapping.setdefault(candidate_type, []).append(domain["context_domain_id"])
    return {key: sorted(value) for key, value in sorted(mapping.items())}
