from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_recommendation_shadow_eval_scores_negative_and_positive_context_without_serving() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    fixture = _fixture_payload()
    fixture["candidate_pool"].append(
        {
            "candidate_id": "food-cilantro",
            "name": "cilantro chicken bowl",
            "source": "fixture",
            "estimated_kcal": 690,
            "tags": ["lunch"],
        }
    )

    artifact = build_shadow_lab_artifacts(fixture)["recommendation_shadow_eval"]

    assert artifact["recommendation_served"] is False
    assert artifact["live_search_used"] is False
    assert artifact["intake_commit_requested"] is False
    assert {
        "golden-order-morning-bar-oatmeal-latte",
        "preference-drink-latte",
        "negative-preference-ingredient-cilantro",
        "temporary-preference-lower-oil-dinner",
    }.issubset(set(artifact["used_context_candidate_ids"]))

    by_id = {
        evaluation["candidate"]["candidate_id"]: evaluation
        for evaluation in artifact["candidate_evaluations"]
    }
    assert (
        by_id["food-1"]["review_only_score"]
        > by_id["food-cilantro"]["review_only_score"]
    )
    assert by_id["food-1"]["positive_context_matches"]
    assert by_id["food-cilantro"]["blocked_by_negative_preference"] is True
    assert "negative_preference_match" in by_id["food-cilantro"]["ranking_basis"]
    assert all(
        evaluation["runtime_effect_allowed"] is False
        for evaluation in artifact["candidate_evaluations"]
    )
