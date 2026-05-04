from __future__ import annotations


from tests.long_term_context_shadow_fixture import _fixture_payload


def test_shadow_replay_evaluators_explain_used_and_ignored_context() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "shadow_replay_evaluators"
    ]

    assert artifact["artifact_type"] == "shadow_replay_evaluators"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["recommendation_served"] is False
    assert artifact["intake_commit_requested"] is False
    assert artifact["calibration_math_changed"] is False

    assert set(artifact["replays"]) == {
        "recommendation_shadow_replay",
        "intake_clarification_shadow_replay",
        "calibration_bias_shadow_replay",
        "conversation_recall_shadow_replay",
    }

    recommendation = artifact["replays"]["recommendation_shadow_replay"]
    assert recommendation["expected_user_value"] == "better_candidate_ranking_review"
    assert recommendation["menu_scan_context_used_as_candidate_source"] is True
    assert recommendation["runtime_recommendation_mode_started"] is False
    assert (
        "golden-order-morning-bar-oatmeal-latte" in recommendation["used_candidate_ids"]
    )
    assert recommendation["ignored_candidates"]

    intake = artifact["replays"]["intake_clarification_shadow_replay"]
    assert intake["expected_user_value"] == "fewer_but_better_followups_review"
    assert intake["clarification_policy"] in {
        "ask_targeted_followup",
        "use_phrase_pattern_with_caution",
    }
    assert any(
        candidate_id.startswith("user-language-")
        for candidate_id in intake["used_candidate_ids"]
    )

    calibration = artifact["replays"]["calibration_bias_shadow_replay"]
    assert calibration["expected_user_value"] == "better_bias_attribution_review"
    assert calibration["does_not_change_calibration_math"] is True
    assert calibration["bias_attribution"]["likely_underestimate_candidate_ids"] == [
        "intake-estimation-bias-likely-underestimate"
    ]
    assert calibration["bias_attribution"]["likely_overestimate_candidate_ids"] == []
    assert calibration["bias_attribution"]["math_adjustment_allowed"] is False
    assert (
        "intake-estimation-bias-likely-underestimate"
        in calibration["used_candidate_ids"]
    )

    conversation = artifact["replays"]["conversation_recall_shadow_replay"]
    assert conversation["expected_user_value"] == "better_cross_session_context_review"
    assert conversation["manager_tool_call_allowed"] is False
    assert conversation["raw_transcript_injected"] is False
    assert "conversation-recall-context-summary" in conversation["used_candidate_ids"]


def test_review_queue_reducer_prioritizes_product_value_without_artifact_sprawl() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())["review_queue_reducer"]

    assert artifact["artifact_type"] == "review_queue_reducer"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["artifact_sprawl_control"] == {
        "new_artifact_requires_declared_consumer": True,
        "new_artifact_requires_scoring_or_replay_use": True,
        "consumerless_candidates_deferred": True,
    }

    queue = artifact["review_queue"]
    assert set(queue) == {"high", "medium", "low", "rejected_or_deferred"}
    assert queue["high"]
    assert any(
        item["candidate_id"] == "negative-preference-ingredient-cilantro"
        for item in queue["high"]
    )
    assert all(
        item["runtime_effect_allowed"] is False
        for bucket in queue.values()
        for item in bucket
    )
    assert artifact["summary"]["candidate_count"] == sum(
        len(items) for items in queue.values()
    )
    assert artifact["summary"]["pseudo_runtime_truth_risk_count"] == 0

    reviews = {
        item["mechanism_id"]: item for item in artifact["deferred_mechanism_reviews"]
    }
    assert {
        "active_conversation_recall_tool",
        "durable_memory_write_service",
        "semantic_pattern_llm_extraction",
        "style_profile_materialization",
        "live_menu_scan_runtime",
    }.issubset(reviews)
    assert all(item["product_capability_value"] for item in reviews.values())
    assert all(item["blocked_by_dependency"] is True for item in reviews.values())


def test_context_pack_token_pressure_shadow_eval_preserves_l4c_ordering() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "context_pack_token_pressure_shadow_eval"
    ]

    assert artifact["artifact_type"] == "context_pack_token_pressure_shadow_eval"
    assert artifact["source_spec"] == "docs/specs/L4C_CONTEXT_PACKING_SPEC.md"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["token_pressure_policy"] == {
        "general_compaction_threshold": 0.6,
        "aggressive_compaction_threshold": 0.8,
        "forced_trim_threshold": 0.9,
    }
    assert artifact["prune_order"][:2] == [
        "long_transcript",
        "raw_historical_records",
    ]
    assert "current_task_object" in artifact["preserve_first"]
    assert "atomic_context_blocks" in artifact["preserve_first"]
    assert artifact["atomic_blocks_split_allowed"] is False
    assert {pack["pack_id"] for pack in artifact["evaluated_packs"]} >= {
        "recommendation",
        "intake_chat_context",
        "calibration_context",
        "proactive_context",
        "rescue_context",
        "cross_surface_context",
    }
    assert all(
        pack["raw_full_history_dumped"] is False for pack in artifact["evaluated_packs"]
    )


def test_product_capability_context_map_covers_whole_product_memory_consumers() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "product_capability_context_map"
    ]

    assert artifact["artifact_type"] == "product_capability_context_map"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["canonical_truth_replaced_by_memory"] is False
    assert {family["family_id"] for family in artifact["capability_families"]} == {
        "F1",
        "F2",
        "F3",
        "F4",
        "F5",
        "F6",
        "F7",
        "F8",
    }

    domain_ids = {domain["context_domain_id"] for domain in artifact["context_domains"]}
    assert {
        "food_preference_context",
        "negative_preference_context",
        "temporary_preference_context",
        "golden_order_context",
        "user_language_semantic_alias_context",
        "intake_estimation_bias_context",
        "app_usage_style_context",
        "interaction_preference_context",
        "logging_adherence_context",
        "conversation_recall_context",
        "proactive_suppression_context",
        "rescue_history_context",
        "calibration_quality_context",
        "cross_surface_context",
    }.issubset(domain_ids)

    by_family = {
        family["family_id"]: family for family in artifact["capability_families"]
    }
    assert "food_preference_context" in by_family["F6"]["context_domain_ids"]
    assert (
        "user_language_semantic_alias_context" in by_family["F2"]["context_domain_ids"]
    )
    assert "intake_estimation_bias_context" in by_family["F5"]["context_domain_ids"]
    assert "conversation_recall_context" in by_family["F8"]["context_domain_ids"]
    assert "proactive_suppression_context" in by_family["F7"]["context_domain_ids"]

    consumer_ids = {
        consumer["consumer_id"] for consumer in artifact["consumer_contracts"]
    }
    assert {
        "recommendation",
        "intake_clarification",
        "chat_context",
        "calibration",
        "proactive",
        "rescue_later",
        "cross_surface_experience",
    }.issubset(consumer_ids)

    assert (
        "negative_preference"
        not in artifact["coverage_gaps"]["fixture_missing_candidate_types"]
    )
    assert (
        "temporary_preference"
        not in artifact["coverage_gaps"]["fixture_missing_candidate_types"]
    )
    assert "docs/specs/L4A_MEMORY_MODEL_SPEC.md" in artifact["source_specs"]
    assert "docs/specs/L4C_CONTEXT_PACKING_SPEC.md" in artifact["source_specs"]


def test_review_actions_create_shadow_records_without_durable_memory_write() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "memory_review_action_shadow_result"
    ]

    assert artifact["artifact_type"] == "memory_review_action_shadow_result"
    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["summary"] == {
        "action_count": 2,
        "accepted_count": 1,
        "rejected_count": 1,
        "shadow_memory_record_count": 1,
        "missing_target_count": 0,
    }

    accepted = next(
        result
        for result in artifact["candidate_review_results"]
        if result["candidate_id"] == "user-language-正常便當"
    )
    assert accepted["review_status_after"] == "accepted"
    assert accepted["runtime_effect_allowed"] is False
    assert accepted["durable_memory_write_allowed"] is False

    record = artifact["shadow_memory_records"][0]
    assert record["source_candidate_id"] == "user-language-正常便當"
    assert record["record_state"] == "accepted_shadow"
    assert record["can_be_runtime_loaded"] is False
    assert record["durable_memory_written"] is False
    assert record["provenance"]["source_trace_ids"] == ["lang-1"]


def test_memory_promotion_demotion_shadow_eval_never_writes_durable_memory() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "memory_promotion_demotion_shadow_eval"
    ]

    assert artifact["artifact_type"] == "memory_promotion_demotion_shadow_eval"
    assert artifact["promotion_attempted"] is False
    assert artifact["demotion_attempted"] is False
    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["source_spec"] == "docs/specs/L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md"

    by_id = {item["candidate_id"]: item for item in artifact["promotion_review_items"]}
    language_item = next(
        item
        for item in artifact["promotion_review_items"]
        if item["candidate_id"].startswith("user-language-")
    )
    assert language_item["review_action_status"] == "accepted"
    assert language_item["durable_write_allowed"] is False
    assert by_id["negative-preference-ingredient-cilantro"]["promotion_blockers"] == [
        "human_confirmation_required"
    ]
    assert (
        by_id["temporary-preference-lower-oil-dinner"]["temporal_validity_required"]
        is True
    )
    assert by_id["temporary-preference-lower-oil-dinner"]["promotion_blockers"] == [
        "human_confirmation_required",
        "expiry_policy_required",
    ]

    demotion_lanes = {
        lane["lane_id"]: lane for lane in artifact["demotion_review_lanes"]
    }
    assert (
        demotion_lanes["expired_temporary_preference"]["automatic_runtime_effect"]
        is False
    )
    assert (
        demotion_lanes["user_correction_or_deletion"]["human_review_required"] is True
    )


def test_semantic_pattern_extraction_shadow_plan_keeps_llm_extraction_disabled() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "semantic_pattern_extraction_shadow_plan"
    ]

    assert artifact["artifact_type"] == "semantic_pattern_extraction_shadow_plan"
    assert artifact["source_spec"] == "docs/specs/L4A_MEMORY_MODEL_SPEC.md"
    assert artifact["llm_extraction_called"] is False
    assert artifact["semantic_memory_written"] is False
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["readiness_gate"] == {
        "required_new_committed_meal_items": 21,
        "required_days_since_last_extraction": 7,
        "fixture_committed_meal_items": 4,
        "extraction_allowed_now": False,
        "block_reason": "insufficient_committed_meal_items",
    }
    assert artifact["planned_output_schema"]["pattern_type_values"] == [
        "contextual_preference",
        "temporal_preference",
        "trend_shift",
        "situational_avoidance",
    ]
    assert artifact["intended_consumers"] == [
        "recommendation",
        "nightly_insight",
        "confirmed_memory_candidate_review",
    ]
    assert artifact["shadow_extraction_candidates"][0]["pattern_type"] == (
        "temporal_preference"
    )
    assert (
        artifact["shadow_extraction_candidates"][0]["durable_memory_write_allowed"]
        is False
    )
