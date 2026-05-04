from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_consumer_memory_substrate_aligns_l4a_layers_without_runtime_writes() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "consumer_memory_substrate_shadow_eval"
    ]

    assert artifact["artifact_type"] == "consumer_memory_substrate_shadow_eval"
    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["source_specs"] == [
        "docs/specs/L4A_MEMORY_MODEL_SPEC.md",
        "docs/specs/L4C_CONTEXT_PACKING_SPEC.md",
        "docs/specs/L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md",
        "docs/specs/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md",
        "docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md",
        "docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md",
        "docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md",
    ]

    layers = {layer["layer_id"]: layer for layer in artifact["memory_layers"]}
    assert layers["l1_typed_history"]["runtime_truth_owner"] == (
        "canonical_product_objects"
    )
    assert layers["l2a_statistical_pattern"]["selection_role"] == (
        "deterministic_consumer_signal"
    )
    assert layers["l2b_semantic_pattern"]["activation_allowed_now"] is False
    assert layers["l3_confirmed_memory"]["durable_write_allowed_now"] is False
    assert layers["derived_views"]["runtime_materialization_allowed_now"] is False

    assert artifact["global_selection_policy"] == {
        "negative_preference_overrides_positive": True,
        "temporary_preference_requires_validity_window": True,
        "golden_orders_are_materialized_views": True,
        "stale_pattern_downgraded_not_deleted": True,
        "confirmed_memory_requires_human_review": True,
        "raw_history_dump_forbidden": True,
    }


def test_recommendation_memory_bundle_is_primary_and_blocks_negative_matches() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "consumer_memory_substrate_shadow_eval"
    ]

    recommendation = artifact["consumer_memory_bundles"]["recommendation"]
    assert recommendation["consumer_priority"] == 1
    assert recommendation["required_memory_domains"] == [
        "preference_profile_summary",
        "golden_order_summary",
        "negative_preference_memory",
        "temporary_preference_memory",
        "store_familiarity",
        "calibration_quality_context",
    ]
    assert recommendation["hard_guards"] == [
        "confirmed_or_reviewed_negative_preference",
        "budget_fit",
        "temporary_preference_validity",
    ]
    assert (
        "negative-preference-ingredient-cilantro"
        in recommendation["blocking_memory_candidate_ids"]
    )
    assert (
        "golden-order-morning-bar-oatmeal-latte"
        in recommendation["ranking_memory_candidate_ids"]
    )
    assert recommendation["runtime_serving_allowed"] is False
    assert recommendation["missing_runtime_dependencies"] == [
        "recommendation_context_result_contract",
        "candidate_spec_generation_runtime",
        "ranking_and_synthesis_runtime",
        "user_visible_memory_review_surface",
    ]


def test_proactive_calibration_and_rescue_bundles_share_memory_without_mutation() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "consumer_memory_substrate_shadow_eval"
    ]

    proactive = artifact["consumer_memory_bundles"]["proactive"]
    assert proactive["required_memory_domains"] == [
        "suppression_summary",
        "app_usage_style_memory",
        "interaction_preference_memory",
        "logging_adherence_memory",
        "recommendation_memory_quality",
    ]
    assert proactive["surface_policy"] == "no_send_shadow_only"
    assert proactive["runtime_serving_allowed"] is False
    assert proactive["blocking_memory_candidate_ids"]

    calibration = artifact["consumer_memory_bundles"]["calibration"]
    assert calibration["required_memory_domains"] == [
        "intake_completeness_summary",
        "adherence_summary",
        "calibration_history_summary",
        "intake_estimation_bias_memory",
    ]
    assert (
        "intake-estimation-bias-likely-underestimate"
        in calibration["attribution_memory_candidate_ids"]
    )
    assert calibration["math_mutation_allowed"] is False

    rescue = artifact["consumer_memory_bundles"]["rescue_later"]
    assert rescue["required_memory_domains"] == [
        "rescue_history_summary",
        "adherence_summary",
        "recent_overshoot_pattern",
        "interaction_preference_memory",
    ]
    assert (
        "pattern-budget-overshoot-frequency" in rescue["viability_memory_candidate_ids"]
    )
    assert rescue["proposal_commit_allowed"] is False


def test_memory_extraction_storage_rag_plan_separates_raw_and_canonical_truth() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "memory_extraction_storage_rag_shadow_plan"
    ]

    assert artifact["artifact_type"] == "memory_extraction_storage_rag_shadow_plan"
    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["source_references_checked"] == [
        "docs/specs/L4A_MEMORY_MODEL_SPEC.md",
        "docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md",
        "docs/specs/L4C_CONTEXT_PACKING_SPEC.md",
        "docs/specs/L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md",
        "https://openai.github.io/openai-agents-python/sessions/",
        "https://openai.github.io/openai-agents-python/sandbox/memory/",
        "https://openai.github.io/openai-agents-python/guardrails/",
        "https://code.claude.com/docs/en/memory",
        "https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool",
        "https://docs.langchain.com/oss/python/concepts/memory",
        "https://github.com/openclaw/openclaw/blob/main/docs/concepts/memory.md",
        "https://docs.openclaw.ai/concepts/memory-search",
        "https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers",
        "local_hindsight_docs_read_only",
        "local_agent_runtime_skills_read_only",
    ]

    stores = {store["store_id"]: store for store in artifact["storage_zones"]}
    assert stores["raw_trace_archive"]["stores_raw_user_input"] is True
    assert stores["canonical_product_store"]["stores_runtime_truth"] is True
    assert stores["derived_memory_candidate_store"]["runtime_truth_owner"] == (
        "shadow_lab"
    )
    assert stores["reviewed_memory_store_future"]["write_allowed_now"] is False
    assert stores["retrieval_index_future"]["index_build_allowed_now"] is False

    assert artifact["raw_vs_canonical_policy"] == {
        "raw_user_input_kept_as_evidence_only": True,
        "meal_thread_is_canonical_meal_truth": True,
        "fooddb_is_canonical_nutrition_truth": True,
        "memory_may_reference_but_not_replace_canonical_objects": True,
        "derived_memory_candidates_require_source_refs": True,
        "confirmed_memory_requires_human_review": True,
    }

    lanes = {lane["lane_id"]: lane for lane in artifact["extraction_lanes"]}
    assert lanes["explicit_user_statement"]["llm_allowed_now"] is False
    assert lanes["canonical_history_consolidation"]["deterministic_allowed_now"] is True
    assert lanes["correction_lineage"]["product_capability_value"] == (
        "calibration_bias_and_intake_clarification"
    )
    assert lanes["proactive_suppression_feedback"]["write_to_scheduler"] is False

    rag = artifact["retrieval_and_rag_policy"]
    assert rag["rag_is_not_default_memory_architecture"] is True
    assert rag["metadata_filter_before_vector_search"] is True
    assert rag["consumer_specific_retrieval_budgets"]["recommendation"] == "medium"
    assert rag["raw_full_history_dump_allowed"] is False
    assert rag["active_runtime_tool_registered"] is False

    assert {
        "recommendation",
        "intake_clarification",
        "calibration",
        "proactive",
        "rescue_later",
        "chat_context",
    }.issubset(set(artifact["product_capability_fit"]))
