from __future__ import annotations


from tests.long_term_context_shadow_fixture import _fixture_payload


def test_conversation_recall_shadow_eval_is_summary_first_and_tool_call_disabled() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "conversation_recall_shadow_eval"
    ]

    assert artifact["artifact_type"] == "conversation_recall_shadow_eval"
    assert artifact["summary_first"] is True
    assert artifact["raw_transcript_included"] is False
    assert artifact["retrieval_tool_called"] is False
    assert artifact["manager_tool_call_allowed"] is False
    assert artifact["manager_context_injected"] is False
    assert (
        artifact["selected_context_candidates"][0]["candidate_type"]
        == "conversation_recall_context"
    )
    assert (
        artifact["selected_context_candidates"][0]["would_load_full_history"] is False
    )
    assert artifact["omission_trace"] == {
        "raw_transcript_omitted": True,
        "full_history_dump_omitted": True,
        "runtime_packet_injection_omitted": True,
    }


def test_conversation_recall_tool_shadow_plan_keeps_future_retrieval_disabled() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "conversation_recall_tool_shadow_plan"
    ]

    assert artifact["artifact_type"] == "conversation_recall_tool_shadow_plan"
    assert artifact["context_entry_mode"] == (
        "future_tool_mediated_retrieval_candidate"
    )
    assert artifact["manager_tool_registered"] is False
    assert artifact["manager_tool_called"] is False
    assert artifact["runtime_tool_available"] is False
    assert artifact["retrieval_tool_call_allowed_now"] is False
    assert artifact["raw_transcript_access_allowed_now"] is False
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["manager_context_injected"] is False

    contract = artifact["future_tool_contract"]
    assert contract["tool_name"] == "conversation_recall.search"
    assert contract["request_schema"]["required"] == [
        "user_id",
        "retrieval_query",
        "scope",
        "reason_for_recall",
    ]
    assert contract["response_contract"]["summary_first"] is True
    assert contract["response_contract"]["source_refs_required"] is True
    assert contract["response_contract"]["raw_transcript_returned"] is False
    assert contract["response_contract"]["manager_context_injection_allowed"] is False
    assert artifact["selected_conversation_refs"][0]["candidate_id"] == (
        "conversation-recall-context-summary"
    )
    assert (
        "ManagerContextPacket injection remains forbidden"
        in artifact["safety_boundaries"]
    )


def test_conversation_recall_retrieval_shadow_eval_routes_without_tool_calls() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "conversation_recall_retrieval_shadow_eval"
    ]

    assert artifact["artifact_type"] == "conversation_recall_retrieval_shadow_eval"
    assert artifact["retrieval_tool_registered"] is False
    assert artifact["retrieval_tool_called"] is False
    assert artifact["live_vector_search_used"] is False
    assert artifact["raw_transcript_returned"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["source_classes"] == [
        "conversation_history_summary",
        "memory_candidate_review_artifact",
    ]
    assert artifact["routing_policy"] == {
        "deterministic_scope_filter_first": True,
        "metadata_filter_before_semantic_search": True,
        "full_document_read_fallback_allowed": False,
        "stale_result_requires_review": True,
    }
    assert artifact["ranked_results"][0]["candidate_id"] == (
        "conversation-recall-context-summary"
    )
    assert artifact["negative_cases"][0] == {
        "case_id": "missing_user_scope",
        "retrieval_allowed": False,
        "reason": "scope_keys_required_before_recall",
    }


def test_context_ingress_decision_shadow_eval_separates_memory_from_transcript_and_truth() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "context_ingress_decision_shadow_eval"
    ]

    assert artifact["artifact_type"] == "context_ingress_decision_shadow_eval"
    assert artifact["manager_tool_registered"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["runtime_context_loaded"] is False
    assert artifact["context_ingress_modes"] == [
        "shadow_artifact_review",
        "summary_first_context_pack",
        "future_tool_mediated_recall",
    ]

    by_state = {
        state["state_class"]: state for state in artifact["memory_state_taxonomy"]
    }
    assert by_state["l1_typed_history_observation"]["truth_role"] == (
        "canonical_source"
    )
    assert by_state["l2_pattern_inference"]["truth_role"] == "derived_candidate"
    assert (
        by_state["l3_profile_or_confirmed_memory_future"]["runtime_write_allowed_now"]
        is False
    )
    assert by_state["conversation_recall_summary"]["raw_transcript_returned"] is False

    decisions = {
        decision["decision_id"]: decision
        for decision in artifact["source_of_meaning_decisions"]
    }
    assert decisions["canonical_truth_not_replaced_by_memory"]["enforced_now"] is True
    assert (
        decisions["conversation_recall_is_context_ingress_not_memory_write"][
            "future_tool_call_allowed_now"
        ]
        is False
    )


def test_entity_normalization_shadow_plan_stays_review_only() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "entity_normalization_shadow_plan"
    ]

    assert artifact["artifact_type"] == "entity_normalization_shadow_plan"
    assert artifact["entity_store_written"] is False
    assert artifact["fooddb_truth_changed"] is False
    assert artifact["canonical_objects_replaced"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["entity_types"] == [
        "food_item",
        "store",
        "user_phrase",
        "preference_value",
        "conversation_topic",
    ]
    proposed_ids = {entity["entity_id"] for entity in artifact["proposed_entities"]}
    assert "store-morning-bar" in proposed_ids
    assert "food-oatmeal" in proposed_ids
    assert "preference-value-cilantro" in proposed_ids
    assert artifact["normalization_review_lanes"][0]["runtime_effect_allowed"] is False


def test_context_quality_contradiction_review_flags_shadow_conflicts() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    fixture = _fixture_payload()
    fixture["candidate_pool"].append(
        {"candidate_id": "food-cilantro", "name": "cilantro chicken bowl"}
    )

    artifact = build_shadow_lab_artifacts(fixture)[
        "context_quality_contradiction_review_queue"
    ]

    assert artifact["artifact_type"] == "context_quality_contradiction_review_queue"
    assert artifact["runtime_blocking_claimed"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["contradiction_count"] >= 1
    conflict = next(
        item
        for item in artifact["review_items"]
        if item["check_id"] == "negative_preference_vs_candidate_pool"
    )
    assert conflict["review_status"] == "pending"
    assert conflict["runtime_effect_allowed"] is False
    assert conflict["recommended_action"] == "keep_shadowing"
    assert "negative-preference-ingredient-cilantro" in conflict["candidate_ids"]


def test_capability_scenario_fixture_pack_covers_consumer_paths_without_runtime() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "capability_scenario_fixture_pack"
    ]

    assert artifact["artifact_type"] == "capability_scenario_fixture_pack"
    assert artifact["runtime_scenarios_executed"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["fixture_only"] is True
    assert {scenario["consumer_id"] for scenario in artifact["scenarios"]} == {
        "recommendation",
        "intake_clarification",
        "chat_context",
        "calibration",
        "proactive",
        "rescue_later",
        "conversation_recall",
    }
    for scenario in artifact["scenarios"]:
        assert scenario["runtime_effect_allowed"] is False
        assert scenario["expected_artifact_ids"]
        assert scenario["forbidden_runtime_effects"]


def test_pr_review_autopilot_closeout_is_draft_pr_only() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "pr_review_autopilot_closeout"
    ]

    assert artifact["artifact_type"] == "pr_review_autopilot_closeout"
    assert artifact["draft_pr_only"] is True
    assert artifact["auto_merge_allowed"] is False
    assert artifact["human_approval_required_for_merge"] is True
    assert artifact["continue_same_draft_pr_after_ci_green"] is True
    assert artifact["stop_after_pr_push"] is False
    assert artifact["merge_still_requires_human_approval"] is True
    assert artifact["offline_shadow_completion_audit"] == {
        "completion_status": "complete_for_no_runtime_scope",
        "remaining_buildable_without_runtime_dependencies": [],
        "runtime_or_storage_dependency_required_for_next_stage": True,
    }
    assert {
        "durable_memory_write_service",
        "manager_context_retrieval_tool",
        "active_context_pack_injection",
    }.issubset(set(artifact["blocked_future_runtime_slices"]))
    assert artifact["runtime_effect_allowed"] is False


def test_consumer_specific_context_packs_are_summary_first_and_non_injecting() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "long_term_context_pack_shadow_eval"
    ]

    assert artifact["artifact_type"] == "long_term_context_pack_shadow_eval"
    assert artifact["manager_context_injected"] is False
    assert artifact["runtime_context_loaded"] is False
    assert set(artifact["context_packs"]) == {
        "recommendation",
        "intake_chat_context",
        "calibration_context",
        "proactive_context",
        "rescue_context",
        "cross_surface_context",
    }

    for pack in artifact["context_packs"].values():
        assert pack["summary_first"] is True
        assert pack["structured_state_first"] is True
        assert pack["raw_full_history_dumped"] is False
        assert pack["runtime_effect_allowed"] is False
        assert pack["manager_context_injection_allowed"] is False
        assert pack["token_estimate"] >= 0
        assert pack["omission_trace"]["raw_transcript_omitted"] is True
        assert pack["omission_trace"]["unselected_candidates_omitted"] >= 0

    recommendation = artifact["context_packs"]["recommendation"]
    assert (
        "golden-order-morning-bar-oatmeal-latte"
        in recommendation["selected_candidate_ids"]
    )
    assert "preference-drink-latte" in recommendation["selected_candidate_ids"]
    assert (
        "negative-preference-ingredient-cilantro"
        in recommendation["selected_candidate_ids"]
    )
    assert (
        "temporary-preference-lower-oil-dinner"
        in recommendation["selected_candidate_ids"]
    )

    intake_chat = artifact["context_packs"]["intake_chat_context"]
    assert any(
        candidate_id.startswith("user-language-")
        for candidate_id in intake_chat["selected_candidate_ids"]
    )
    assert (
        "conversation-recall-context-summary" in intake_chat["selected_candidate_ids"]
    )

    calibration = artifact["context_packs"]["calibration_context"]
    assert (
        "intake-estimation-bias-likely-underestimate"
        in calibration["selected_candidate_ids"]
    )
    assert "pattern-budget-overshoot-frequency" in calibration["selected_candidate_ids"]

    proactive = artifact["context_packs"]["proactive_context"]
    assert "app-usage-style-pattern" in proactive["selected_candidate_ids"]
    assert (
        "interaction-preference-prefers-direct-calorie-numbers"
        in proactive["selected_candidate_ids"]
    )

    rescue = artifact["context_packs"]["rescue_context"]
    assert "pattern-budget-overshoot-frequency" in rescue["selected_candidate_ids"]
    assert "pattern-weight-logging-consistency" in rescue["selected_candidate_ids"]

    cross_surface = artifact["context_packs"]["cross_surface_context"]
    assert "app-usage-style-pattern" in cross_surface["selected_candidate_ids"]
    assert (
        "conversation-recall-context-summary" in cross_surface["selected_candidate_ids"]
    )


def test_shadow_simulations_never_send_serve_or_commit() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifacts = build_shadow_lab_artifacts(_fixture_payload())

    proactive = artifacts["proactive_no_send_simulation"]
    assert proactive["proactive_sent"] is False
    assert proactive["scheduler_activated"] is False
    assert proactive["would_inject_context"] is False
    assert proactive["injection_position"] == "not_applicable_shadow"
    assert proactive["token_estimate"] >= 0
    assert proactive["candidate_triggers"]

    recommendation = artifacts["recommendation_shadow_eval"]
    assert recommendation["recommendation_served"] is False
    assert recommendation["live_search_used"] is False
    assert recommendation["candidate_evaluations"]
    used_context_ids = recommendation["candidate_evaluations"][0][
        "used_context_candidate_ids"
    ]
    assert "preference-drink-latte" in used_context_ids

    rescue = artifacts["rescue_shadow_candidates"]
    assert rescue["rescue_committed"] is False
    assert rescue["budget_mutation_requested"] is False
    assert rescue["candidate_packets"]

    trigger_ids = {trigger["trigger_id"] for trigger in proactive["candidate_triggers"]}
    assert "trigger-preference-drink-latte" in trigger_ids
