from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_retrieval_ranking_policy_shadow_eval_uses_hybrid_rankers_without_live_index() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "retrieval_ranking_policy_shadow_eval"
    ]

    assert artifact["artifact_type"] == "retrieval_ranking_policy_shadow_eval"
    assert artifact["active_runtime_index_built"] is False
    assert artifact["live_vector_search_used"] is False
    assert artifact["embedding_provider_called"] is False
    assert artifact["manager_tool_registered"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["raw_full_history_dump_allowed"] is False

    assert artifact["ranking_pipeline"] == [
        "scope_and_privacy_filter",
        "canonical_state_first",
        "structured_and_keyword_retrieval",
        "semantic_vector_retrieval_future",
        "hybrid_score_merge",
        "freshness_temporal_decay",
        "mmr_diversification",
        "risk_and_negative_signal_filter",
        "summary_first_context_pack",
    ]
    assert artifact["retrieval_policy"]["metadata_filter_before_vector_search"] is True
    assert artifact["retrieval_policy"]["bm25_keyword_path_required"] is True
    assert artifact["retrieval_policy"]["vector_path_future_only"] is True
    assert artifact["retrieval_policy"]["temporal_decay_required"] is True
    assert artifact["retrieval_policy"]["mmr_diversity_required"] is True
    assert artifact["retrieval_policy"]["reciprocal_rank_fusion_allowed_later"] is True

    assert artifact["consumer_result_budgets"]["proactive"] == {
        "max_results": 2,
        "minimum_precision_posture": "high",
        "silence_allowed_when_uncertain": True,
    }
    assert artifact["deterministic_boundary"]["may_rank_candidates"] is True
    assert artifact["deterministic_boundary"]["may_create_semantic_meaning"] is False
    assert artifact["llm_boundary"]["may_summarize_selected_sources_later"] is True
    assert artifact["llm_boundary"]["may_promote_memory_without_human_review"] is False

    blocked = {case["case_id"]: case for case in artifact["blocked_cases"]}
    assert blocked["missing_scope_keys"]["retrieval_allowed"] is False
    assert blocked["raw_transcript_only_query"]["retrieval_allowed"] is False
    assert blocked["stale_conflicting_memory"]["recommended_action"] == (
        "downgrade_or_human_review"
    )
