from __future__ import annotations


from tests.long_term_context_shadow_fixture import _fixture_payload


def test_memory_candidate_review_preserves_provenance_and_never_promotes_memory() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "long_term_memory_candidate_review"
    ]

    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["summary"]["candidate_count"] >= 4
    assert artifact["summary"]["golden_order_candidate_count"] == 1

    candidates = artifact["candidates"]
    oatmeal = next(
        candidate
        for candidate in candidates
        if candidate["candidate_type"] == "golden_order"
    )
    assert oatmeal["review_status"] == "pending"
    assert oatmeal["human_review_required"] is True
    assert oatmeal["runtime_effect_allowed"] is False
    assert oatmeal["source_trace_ids"] == ["meal-1", "meal-2", "meal-3"]
    assert oatmeal["source_object_refs"] == [
        "MealThread:m1",
        "MealThread:m2",
        "MealThread:m3",
    ]
    assert (
        oatmeal["proposed_memory_text"]
        == "Possible golden order: Morning Bar - oatmeal, latte"
    )
    assert oatmeal["scope_keys"] == {
        "user_id": "fixture-user",
        "workspace_id": "fixture_workspace",
        "project_id": "fixture_project",
        "surface": "fixture_shadow_lab",
    }
    assert oatmeal["secret_scan"]["status"] == "passed_no_secret_fields_detected"
    assert oatmeal["injection_eligibility"] == {
        "eligible": False,
        "reason": "shadow_lab_no_runtime_injection",
    }
    assert oatmeal["runtime_injection_allowed"] is False
    assert oatmeal["intended_consumers"] == [
        "recommendation",
        "intake_clarification",
        "chat_context",
    ]
    assert oatmeal["consumer_use_hints"]
    assert oatmeal["risk_if_wrong"]
    assert oatmeal["promotion_path"] == "human_review_then_l3_confirmed_memory_later"
    assert oatmeal["why_this_is_not_runtime_truth"]
    assert oatmeal["privacy_contract"] == {
        "raw_secret_values_stored": False,
        "scope_keys_required": True,
        "source_refs_required": True,
        "runtime_prompt_injection_allowed": False,
    }
    assert oatmeal["retention_posture"] == "shadow_review_artifact_only"

    for candidate in candidates:
        assert candidate["intended_consumers"]
        assert candidate["consumer_use_hints"]
        assert candidate["risk_if_wrong"]
        assert candidate["promotion_path"]
        assert candidate["why_this_is_not_runtime_truth"]
        assert candidate["runtime_effect_allowed"] is False
        assert candidate["runtime_injection_allowed"] is False


def test_memory_candidate_taxonomy_covers_language_bias_usage_and_interaction_domains() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "long_term_memory_candidate_review"
    ]
    by_type = {
        candidate["candidate_type"]: candidate for candidate in artifact["candidates"]
    }

    assert {
        "user_language_pattern",
        "intake_estimation_bias",
        "app_usage_style",
        "interaction_preference",
        "food_preference",
        "logging_adherence_pattern",
        "negative_preference",
        "temporary_preference",
        "conversation_recall_context",
    }.issubset(by_type)

    language = by_type["user_language_pattern"]
    assert language["payload"]["user_phrase"] == "正常便當"
    assert language["payload"]["pattern_subtype"] == "portion_phrase"
    assert language["payload"]["portion_semantics"] == {
        "portion_label": "normal_meal",
        "expected_components": ["rice", "main", "two_to_three_sides"],
    }
    assert language["intended_consumers"] == [
        "intake_clarification",
        "chat_context",
        "recommendation",
    ]

    bias = by_type["intake_estimation_bias"]
    assert bias["payload"]["bias_direction"] == "likely_underestimate"
    assert set(bias["payload"]["evidence_subtypes"]) == {
        "missed_item_pattern",
        "correction_tendency",
    }
    assert bias["payload"]["missed_item_patterns"] == ["drink_or_sauce"]
    assert bias["payload"]["correction_tendencies"] == ["adds_kcal_after_clarification"]
    assert bias["intended_consumers"] == [
        "calibration",
        "intake_risk_tagging",
        "nutrition_clarify_priority",
        "response_context",
    ]

    usage = by_type["app_usage_style"]
    assert usage["intended_consumers"] == [
        "chat_context",
        "proactive",
        "ux",
        "recommendation_presentation",
    ]

    interaction = by_type["interaction_preference"]
    assert interaction["intended_consumers"] == [
        "response_generation",
        "chat_context",
        "proactive_message_style",
    ]

    logging = by_type["logging_adherence_pattern"]
    assert "calibration" in logging["intended_consumers"]
    assert "rescue_later" in logging["intended_consumers"]

    negative = by_type["negative_preference"]
    assert negative["payload"]["value"] == "cilantro"
    assert negative["intended_consumers"] == [
        "recommendation",
        "proactive",
        "intake_clarification",
    ]

    temporary = by_type["temporary_preference"]
    assert temporary["payload"]["valid_until"] == "2026-04-10"
    assert temporary["intended_consumers"] == [
        "recommendation",
        "chat_context",
        "proactive",
        "intake_clarification",
    ]

    recall = by_type["conversation_recall_context"]
    assert recall["payload"]["summary_first"] is True
    assert recall["payload"]["raw_transcript_included"] is False
    assert recall["payload"]["manager_tool_call_allowed"] is False
    assert recall["intended_consumers"] == [
        "chat_context",
        "intake_clarification",
        "recommendation",
        "calibration",
    ]


def test_context_value_queue_explains_usefulness_and_early_injection_harm() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    queue = build_shadow_lab_artifacts(_fixture_payload())["context_value_review_queue"]

    assert queue["artifact_type"] == "context_value_review_queue"
    assert queue["items"]
    for item in queue["items"]:
        assert item["review_status"] == "pending"
        assert item["human_review_required"] is True
        assert item["runtime_effect_allowed"] is False
        assert item["possible_harm_if_injected_too_early"]
        assert item["recommended_next_action"] in {
            "keep_shadowing",
            "ask_user_to_confirm",
            "promote_to_confirmed_memory_later",
            "discard",
        }


def test_context_signal_quality_scorecard_prioritizes_value_and_harm_review() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "context_signal_quality_scorecard"
    ]

    assert artifact["artifact_type"] == "context_signal_quality_scorecard"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["scorecard_used_for_runtime_ranking"] is False

    by_id = {item["candidate_id"]: item for item in artifact["candidate_scores"]}
    assert (
        by_id["golden-order-morning-bar-oatmeal-latte"]["context_value_level"] == "high"
    )
    assert (
        by_id["intake-estimation-bias-likely-underestimate"]["harm_if_wrong_level"]
        == "high"
    )
    assert (
        by_id["intake-estimation-bias-likely-underestimate"][
            "recommended_review_action"
        ]
        == "keep_shadowing"
    )
    assert (
        by_id["negative-preference-ingredient-cilantro"]["recommended_review_action"]
        == "ask_user_to_confirm"
    )
    assert by_id["temporary-preference-lower-oil-dinner"]["expiry_sensitive"] is True

    rollups = {rollup["consumer_id"]: rollup for rollup in artifact["consumer_rollups"]}
    assert rollups["recommendation"]["candidate_count"] >= 4
    assert (
        "intake-estimation-bias-likely-underestimate"
        in rollups["calibration"]["candidate_ids"]
    )


def test_candidate_extraction_engine_v2_materializes_layers_profile_menu_and_highlights() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "candidate_extraction_engine_v2"
    ]

    assert artifact["artifact_type"] == "candidate_extraction_engine_v2"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["active_menu_scan_runtime_used"] is False

    assert artifact["memory_layers"] == [
        {
            "layer_id": "l1_typed_history_observation",
            "runtime_truth_owner": "canonical_typed_history",
            "durable_memory_written": False,
        },
        {
            "layer_id": "l2a_deterministic_pattern",
            "runtime_truth_owner": "shadow_deterministic_consolidation",
            "durable_memory_written": False,
        },
        {
            "layer_id": "l3_review_candidate_only",
            "runtime_truth_owner": "human_review_future_promotion",
            "durable_memory_written": False,
        },
    ]

    extracted = {
        candidate["candidate_id"]: candidate
        for candidate in artifact["extracted_candidates"]
    }
    language_candidate_id = next(
        candidate_id
        for candidate_id in extracted
        if candidate_id.startswith("user-language-")
    )
    assert "intake-estimation-bias-likely-underestimate" in extracted
    assert extracted[language_candidate_id]["payload_extracts"]["user_phrase"]
    assert extracted["intake-estimation-bias-likely-underestimate"]["payload_extracts"][
        "missed_item_patterns"
    ] == ["drink_or_sauce"]

    profile = artifact["shadow_profile_views"]["preference_profile_summary"]
    assert profile["is_durable_memory_truth"] is False
    assert profile["event_count"] == 4
    assert profile["top_stores"][0] == {"label": "Morning Bar", "count": 3}

    golden = artifact["shadow_profile_views"]["golden_order_summary"]
    assert golden["is_durable_memory_truth"] is False
    assert golden["orders"][0]["store_name"] == "Morning Bar"

    assert (
        artifact["menu_scan_shadow_context"]["runtime_recommendation_mode_started"]
        is False
    )
    assert artifact["menu_scan_shadow_context"]["restaurant_name"] == "Morning Bar"
    assert artifact["menu_scan_shadow_context"]["parsed_item_count"] == 2

    highlights = artifact["weekly_highlight_shadow_candidates"]
    assert highlights["derived_view_only"] is True
    assert "positive_highlights" in highlights
    assert highlights["narrative_summary_generated"] is False


def test_derived_memory_views_shadow_eval_materializes_l4a_summary_views() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "derived_memory_views_shadow_eval"
    ]

    assert artifact["artifact_type"] == "derived_memory_views_shadow_eval"
    assert artifact["derived_views_written_to_runtime"] is False
    assert artifact["canonical_truth_replaced_by_memory"] is False
    assert set(artifact["derived_views"]) == {
        "preference_profile_summary",
        "intake_completeness_summary",
        "adherence_summary",
        "rescue_history_summary",
        "calibration_history_summary",
        "suppression_summary",
        "golden_order_summary",
    }
    for view in artifact["derived_views"].values():
        assert view["source_kind"] == "derived_read_model"
        assert view["is_durable_memory_truth"] is False
        assert view["runtime_effect_allowed"] is False
        assert view["source_refs_required"] is True

    assert (
        artifact["derived_views"]["intake_completeness_summary"]["meal_event_count"]
        == 4
    )
    assert artifact["derived_views"]["adherence_summary"]["overshoot_day_count"] == 1
    assert (
        artifact["derived_views"]["calibration_history_summary"]["latest_bias_posture"]
        == "likely_underestimate_or_expenditure_overestimate"
    )
    assert artifact["derived_views"]["suppression_summary"]["suppression_signals"] == []


def test_context_value_scoring_v2_scores_value_risk_recency_and_actions() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "context_value_scoring_v2"
    ]

    assert artifact["artifact_type"] == "context_value_scoring_v2"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["scorecard_used_for_runtime_ranking"] is False
    assert artifact["score_dimensions"] == [
        "evidence_strength_score",
        "recency_score",
        "frequency_score",
        "consumer_value_score",
        "harm_if_wrong_score",
        "contradiction_penalty",
        "review_priority_score",
    ]

    by_id = {item["candidate_id"]: item for item in artifact["candidate_scores"]}
    golden = by_id["golden-order-morning-bar-oatmeal-latte"]
    assert golden["review_priority_bucket"] == "high"
    assert golden["recommended_action"] == "ask_user_to_confirm"
    assert golden["product_capability_value"] == "direct_recommendation_or_intake_gain"

    bias = by_id["intake-estimation-bias-likely-underestimate"]
    assert bias["harm_if_wrong_level"] == "high"
    assert bias["recommended_action"] == "keep_shadowing"
    assert bias["product_capability_value"] == "calibration_or_clarification_gain"

    assert artifact["action_rollups"]["ask_user_to_confirm"] >= 1
    assert artifact["all_candidates_have_product_capability_value"] is True
