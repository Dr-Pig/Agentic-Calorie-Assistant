from __future__ import annotations

from typing import Any

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)


def build_product_lab_premeal_fixture_inputs(
    *,
    location_available: bool,
) -> dict[str, Any]:
    fixture = build_product_lab_fixture_inputs()
    payload = dict(fixture["recommendation_payload"])
    payload["current_budget_view"] = {"remaining_kcal": 680}
    payload["candidate_source_fixture"] = (
        _located_candidates() if location_available else _fallback_candidates()
    )
    selected_candidate_id = (
        "xinyi-bento-1" if location_available else "history-oatmeal-1"
    )
    selected_store_name = "Xinyi Bento Lab" if location_available else "Morning Bar"
    payload["manager_recommendation_decision_fixture"] = {
        "decision_mode": "llm_fixture",
        "top_candidate_id": selected_candidate_id,
        "decision_summary": "fixture LLM chose a pre-meal budget-fitting option",
    }
    payload["shadow_offer_packet_fixture"] = {
        "decision_mode": "llm_fixture",
        "candidate_id": selected_candidate_id,
        "backup_candidate_ids": [],
        "explanation": "Fixture LLM selected the pre-meal planning option.",
        "recommendation_served": False,
        "is_canonical_truth": False,
        "intake_commit_requested": False,
    }
    payload["pre_meal_planning_context"] = {
        "mode": "pre_meal_planning",
        "location_area": "Xinyi" if location_available else "",
        "location_source": "structured_turn" if location_available else "",
        "budget_source": "current_budget_view.remaining_kcal",
        "preference_source_refs": [
            "memory_summary:golden_order",
            "fixture:negative-1",
        ],
    }
    return {
        **fixture,
        "memory_summary_projection": _memory_projection(
            selected_candidate_id,
            selected_store_name,
        ),
        "recommendation_payload": payload,
    }


def _located_candidates() -> list[dict[str, Any]]:
    return [
        _candidate("xinyi-bento-1", "Xinyi Bento Lab chicken set", 560, "Xinyi", 350),
        _candidate("daan-salad-1", "Daan salad bowl", 520, "Daan", 1800),
        _candidate("xinyi-ramen-1", "Xinyi ramen", 760, "Xinyi", 260),
    ]


def _fallback_candidates() -> list[dict[str, Any]]:
    return [
        {
            **_candidate("history-oatmeal-1", "Morning Bar oatmeal", 420, "", 0),
            "source_type": "golden_order",
            "store_name": "Morning Bar",
            "source_refs": ["memory_candidate:history-oatmeal-1"],
        }
    ]


def _candidate(
    candidate_id: str,
    title: str,
    kcal_max: int,
    location_area: str,
    distance_m: int,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "title": title,
        "source_type": "nearby_fixture",
        "store_name": title.split(" chicken")[0].split(" oatmeal")[0],
        "location_area": location_area,
        "distance_m": distance_m,
        "estimated_kcal": kcal_max,
        "estimated_kcal_range": {"min": max(kcal_max - 130, 0), "max": kcal_max},
        "item_patterns": ["pre_meal_planning_option"],
        "hard_avoid_flags": [],
        "source_refs": [f"memory_candidate:{candidate_id}"],
        "evidence_posture": "exact",
        "availability_posture": "available",
        "realistic_executable": True,
        "user_accessible": True,
    }


def _memory_projection(candidate_id: str, store_name: str) -> dict[str, Any]:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "freshness_posture": "fresh",
            "accepted_shadow_candidate_ids": [candidate_id],
            "negative_preference_blockers": ["neg-1"],
        },
        "golden_order_summary": {
            "orders": [{"candidate_id": candidate_id, "store_name": store_name}]
        },
        "suppression_summary": {"suppression_blockers": []},
    }


__all__ = ["build_product_lab_premeal_fixture_inputs"]
