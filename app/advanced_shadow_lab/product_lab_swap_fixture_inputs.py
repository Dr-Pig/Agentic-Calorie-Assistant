from __future__ import annotations

from typing import Any

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)


def build_product_lab_swap_fixture_inputs(
    *,
    history_sufficient: bool,
) -> dict[str, Any]:
    fixture = build_product_lab_fixture_inputs()
    if not history_sufficient:
        return {
            **fixture,
            "recommendation_payload": {
                **dict(fixture["recommendation_payload"]),
                "swap_suggestion_context": _swap_context(history_sufficient=False),
            },
        }
    payload = {
        **dict(fixture["recommendation_payload"]),
        "current_budget_view": {"remaining_kcal": 700},
        "candidate_source_fixture": [_swap_candidate()],
        "manager_recommendation_decision_fixture": {
            "decision_mode": "llm_fixture",
            "top_candidate_id": "half-sugar-milk-tea-1",
            "decision_summary": "fixture LLM chose the concrete swap option",
        },
        "shadow_offer_packet_fixture": {
            "decision_mode": "llm_fixture",
            "candidate_id": "half-sugar-milk-tea-1",
            "backup_candidate_ids": [],
            "explanation": "Fixture LLM selected the concrete swap suggestion.",
            "recommendation_served": False,
            "is_canonical_truth": False,
            "intake_commit_requested": False,
        },
        "swap_suggestion_context": _swap_context(history_sufficient=True),
    }
    return {
        **fixture,
        "memory_summary_projection": _memory_projection(),
        "recommendation_payload": payload,
    }


def _swap_context(*, history_sufficient: bool) -> dict[str, Any]:
    return {
        "mode": "swap_suggestion",
        "trigger_source": "structured_committed_item_fixture",
        "history_sufficient": history_sufficient,
        "original_item_name": "Full-sugar milk tea",
        "original_kcal": 520,
        "suggested_item_name": "Half-sugar milk tea",
        "suggested_kcal": 380,
        "weekly_frequency_estimate": 7 if history_sufficient else None,
        "suggestion_basis": "preference_pattern" if history_sufficient else "",
        "source_refs": [
            "meal_item:full-sugar-milk-tea",
            "memory_candidate:half-sugar-milk-tea-1",
        ],
    }


def _swap_candidate() -> dict[str, Any]:
    return {
        "candidate_id": "half-sugar-milk-tea-1",
        "title": "Half-sugar milk tea",
        "source_type": "memory_golden_order",
        "store_name": "Tea Stand",
        "estimated_kcal": 380,
        "estimated_kcal_range": {"min": 350, "max": 380},
        "item_patterns": ["milk_tea", "half_sugar"],
        "hard_avoid_flags": [],
        "source_refs": ["memory_candidate:half-sugar-milk-tea-1"],
        "evidence_posture": "exact",
        "availability_posture": "available",
        "realistic_executable": True,
        "user_accessible": True,
    }


def _memory_projection() -> dict[str, Any]:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "freshness_posture": "fresh",
            "accepted_shadow_candidate_ids": ["half-sugar-milk-tea-1"],
            "negative_preference_blockers": ["neg-1"],
        },
        "golden_order_summary": {
            "orders": [
                {
                    "candidate_id": "half-sugar-milk-tea-1",
                    "store_name": "Tea Stand",
                }
            ]
        },
        "suppression_summary": {"suppression_blockers": []},
    }


__all__ = ["build_product_lab_swap_fixture_inputs"]
