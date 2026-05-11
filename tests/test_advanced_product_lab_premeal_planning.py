from __future__ import annotations

from app.advanced_shadow_lab.product_lab_journey_coverage import (
    build_product_lab_journey_coverage_summary,
)
from app.advanced_shadow_lab.product_lab_premeal_fixture_inputs import (
    build_product_lab_premeal_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_recommendation import (
    run_product_lab_recommendation,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from app.advanced_shadow_lab.product_lab_memory import empty_product_lab_memory_context_pack


def test_premeal_planning_recommendation_uses_location_budget_and_preferences() -> None:
    artifact = run_product_lab_recommendation(
        turn=_premeal_turn("q1-xinyi"),
        fixture_inputs=build_product_lab_premeal_fixture_inputs(location_available=True),
        memory_context_pack=empty_product_lab_memory_context_pack(
            session_id="premeal-session",
            turn_id="q1-xinyi",
        ),
    )

    context = artifact["planning"]["recommendation_context_result"]
    assert context["user_goal"] == "pre_meal_planning"
    assert context["raw_user_text_semantic_inference_performed"] is False
    assert context["pre_meal_planning"] == {
        "mode": "pre_meal_planning",
        "location_requested": True,
        "location_area": "Xinyi",
        "location_source": "structured_turn",
        "location_fallback_reason": "",
        "budget_source": "current_budget_view.remaining_kcal",
        "preference_source_refs": ["memory_summary:golden_order", "fixture:negative-1"],
    }
    assert artifact["retrieval_guard_scoring"]["primary_candidate_id"] == "xinyi-bento-1"
    assert artifact["retrieval_guard_scoring"]["filtered_candidates"] == [
        {"candidate_id": "daan-salad-1", "reason_codes": ["location_mismatch"]},
        {"candidate_id": "xinyi-ramen-1", "reason_codes": ["over_budget"]},
    ]
    packet = artifact["offer_synthesis"]["ux_packet"]["pre_meal_planning_packet"]
    assert packet["selected_place"] == {
        "candidate_id": "xinyi-bento-1",
        "store_name": "Xinyi Bento Lab",
        "location_area": "Xinyi",
        "distance_m": 350,
    }
    assert packet["suggested_kcal_range"] == {"min": 430, "max": 560}
    assert packet["remaining_kcal_after_primary_range"] == {"min": 120, "max": 250}
    assert packet["canonical_commit_requested"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["external_location_search_used"] is False


def test_premeal_planning_falls_back_to_preferences_when_location_missing() -> None:
    artifact = run_product_lab_recommendation(
        turn={**_premeal_turn("q1-no-location"), "location_area": ""},
        fixture_inputs=build_product_lab_premeal_fixture_inputs(location_available=False),
        memory_context_pack=empty_product_lab_memory_context_pack(
            session_id="premeal-session",
            turn_id="q1-no-location",
        ),
    )

    context = artifact["planning"]["recommendation_context_result"]["pre_meal_planning"]
    packet = artifact["offer_synthesis"]["ux_packet"]["pre_meal_planning_packet"]

    assert context["location_requested"] is False
    assert context["location_fallback_reason"] == "location_unavailable_fallback_to_preferences"
    assert artifact["retrieval_guard_scoring"]["primary_candidate_id"] == "history-oatmeal-1"
    assert packet["selected_place"]["store_name"] == "Morning Bar"
    assert packet["location_fallback_reason"] == "location_unavailable_fallback_to_preferences"
    assert artifact["blockers"] == []


def test_premeal_planning_turn_surfaces_budget_allocation_advice() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_premeal_turn("q1-turn"),
        fixture_inputs=build_product_lab_premeal_fixture_inputs(location_available=True),
    )

    messages = artifact["lab_chat_surface"]["messages"]
    assert artifact["status"] == "pass"
    assert messages[0]["workflow_family"] == "recommendation"
    assert messages[0]["recommendation_offer"]["pre_meal_planning"]["selected_place"][
        "store_name"
    ] == "Xinyi Bento Lab"
    assert messages[0]["recommendation_offer"]["pre_meal_planning"][
        "budget_allocation_advice"
    ] == "Keep this meal around 430-560 kcal; you should still have 120-250 kcal."
    assert messages[0]["recommendation_offer"]["canonical_commit_requested"] is False
    assert artifact["lab_chat_surface"]["served_to_mainline_user"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def test_journey_coverage_moves_q_after_premeal_planning_evidence() -> None:
    summary = build_product_lab_journey_coverage_summary({})

    assert "Q" in summary["covered_by_existing_executable_evidence_journey_ids"]
    assert summary["product_capability_gap_journey_ids"] == ["V"]
    assert summary["next_product_capability_slice"] == "weekly_insight_proactive_lab"


def _premeal_turn(turn_id: str) -> dict[str, object]:
    return {
        "session_id": "premeal-session",
        "turn_id": turn_id,
        "surface": "chat",
        "semantic_intent_fixture": "pre_meal_planning",
        "turn_mode": "pre_meal_planning",
        "location_area": "Xinyi",
        "user_utterance": "fixture text is not a semantic oracle",
    }
