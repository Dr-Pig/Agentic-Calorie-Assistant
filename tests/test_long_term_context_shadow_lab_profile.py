from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_user_context_profile_shadow_eval_builds_three_layer_profile_without_truth_write() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "user_context_profile_shadow_eval"
    ]

    assert artifact["artifact_type"] == "user_context_profile_shadow_eval"
    assert artifact["profile_materialized_to_runtime"] is False
    assert artifact["structured_user_model_written"] is False
    assert artifact["canonical_truth_replaced_by_profile"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["memory_layer_order"] == [
        "l1_observation_typed_history",
        "l2_inference_shadow_candidates",
        "l3_profile_shadow_review",
    ]

    sections = {
        section["profile_section_id"]: section
        for section in artifact["profile_sections"]
    }
    assert set(sections) == {
        "food_preference_profile",
        "user_language_profile",
        "estimation_bias_profile",
        "app_usage_profile",
        "interaction_preference_profile",
        "adherence_profile",
        "conversation_recall_profile",
    }
    assert "recommendation" in sections["food_preference_profile"]["intended_consumers"]
    assert (
        "intake_clarification"
        in sections["user_language_profile"]["intended_consumers"]
    )
    assert "calibration" in sections["estimation_bias_profile"]["intended_consumers"]
    assert "chat_context" in sections["app_usage_profile"]["intended_consumers"]
    assert (
        "response_generation"
        in sections["interaction_preference_profile"]["intended_consumers"]
    )
    assert "rescue_later" in sections["adherence_profile"]["intended_consumers"]
    assert (
        "future_manager_context_retrieval"
        in sections["conversation_recall_profile"]["intended_consumers"]
    )

    for section in sections.values():
        assert section["source_candidate_ids"]
        assert section["profile_write_allowed"] is False
        assert section["runtime_effect_allowed"] is False
        assert section["risk_if_wrong"]
        assert section["promotion_path"] == "human_review_then_profile_slice_later"
