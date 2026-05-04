from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact


def _retrieval_ranking_policy_shadow_artifact(
    fixture: dict[str, Any],
) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="retrieval_ranking_policy_shadow_eval",
        fixture=fixture,
        extra={
            "source_references_checked": _source_references_checked(),
            "active_runtime_index_built": False,
            "live_vector_search_used": False,
            "embedding_provider_called": False,
            "manager_tool_registered": False,
            "manager_tool_called": False,
            "manager_context_injected": False,
            "raw_full_history_dump_allowed": False,
            "ranking_pipeline": _ranking_pipeline(),
            "retrieval_policy": _retrieval_policy(),
            "consumer_result_budgets": _consumer_result_budgets(),
            "deterministic_boundary": _deterministic_boundary(),
            "llm_boundary": _llm_boundary(),
            "human_boundary": _human_boundary(),
            "blocked_cases": _blocked_cases(),
            "product_capability_value": _product_capability_value(),
        },
    )


def _source_references_checked() -> list[dict[str, str]]:
    return [
        {
            "source": "docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md",
            "adopted": "retrieval intent, source selection, and stale-context review gates remain repo truth.",
        },
        {
            "source": "docs/specs/L4C_CONTEXT_PACKING_SPEC.md",
            "adopted": "summary-first context packing and omission traces are required.",
        },
        {
            "source": "openclaw_memory_search_docs",
            "adopted": "hybrid vector plus BM25 retrieval, temporal decay, and MMR as future retrieval-ranker options.",
        },
        {
            "source": "openai_agents_sessions_docs",
            "adopted": "session history is separate from durable memory; do not load full history as long-term memory.",
        },
        {
            "source": "openai_agents_guardrails_docs",
            "adopted": "tripwire-style guards must sit before user-visible memory use.",
        },
        {
            "source": "hermes_memory_provider_docs",
            "adopted": "provider lifecycle and profile isolation vocabulary only; provider plugins are not activated now.",
        },
    ]


def _ranking_pipeline() -> list[str]:
    return [
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


def _retrieval_policy() -> dict[str, Any]:
    return {
        "scope_filter_before_any_retrieval": True,
        "privacy_filter_before_any_retrieval": True,
        "canonical_state_read_before_memory": True,
        "metadata_filter_before_vector_search": True,
        "bm25_keyword_path_required": True,
        "structured_filter_path_required": True,
        "vector_path_future_only": True,
        "hybrid_merge_future_only": True,
        "reciprocal_rank_fusion_allowed_later": True,
        "temporal_decay_required": True,
        "mmr_diversity_required": True,
        "negative_preferences_can_block_candidates": True,
        "stale_or_conflicting_memory_requires_review": True,
        "summary_first_context_pack_required": True,
        "full_document_read_fallback_allowed": False,
        "raw_transcript_return_allowed": False,
        "runtime_retrieval_permission_now": False,
    }


def _consumer_result_budgets() -> dict[str, dict[str, Any]]:
    return {
        "recommendation": {
            "max_results": 8,
            "minimum_precision_posture": "medium",
            "silence_allowed_when_uncertain": False,
        },
        "intake_clarification": {
            "max_results": 4,
            "minimum_precision_posture": "high",
            "silence_allowed_when_uncertain": False,
        },
        "chat_context": {
            "max_results": 4,
            "minimum_precision_posture": "medium",
            "silence_allowed_when_uncertain": True,
        },
        "calibration": {
            "max_results": 5,
            "minimum_precision_posture": "high",
            "silence_allowed_when_uncertain": False,
        },
        "proactive": {
            "max_results": 2,
            "minimum_precision_posture": "high",
            "silence_allowed_when_uncertain": True,
        },
        "rescue_later": {
            "max_results": 5,
            "minimum_precision_posture": "medium",
            "silence_allowed_when_uncertain": True,
        },
    }


def _deterministic_boundary() -> dict[str, bool]:
    return {
        "may_filter_scope_privacy_and_retention": True,
        "may_rank_candidates": True,
        "may_downgrade_stale_or_conflicting_sources": True,
        "may_enforce_token_and_result_budgets": True,
        "may_create_semantic_meaning": False,
        "may_promote_memory": False,
        "may_override_manager_response": False,
        "may_mutate_canonical_truth": False,
    }


def _llm_boundary() -> dict[str, bool]:
    return {
        "may_summarize_selected_sources_later": True,
        "may_extract_semantic_candidate_later": True,
        "may_generate_live_embedding_now": False,
        "may_promote_memory_without_human_review": False,
        "may_decide_runtime_injection_without_gate": False,
    }


def _human_boundary() -> dict[str, bool]:
    return {
        "must_approve_confirmed_memory": True,
        "must_approve_runtime_injection_gate": True,
        "can_correct_delete_or_suppress_memory_later": True,
        "chat_review_surface_is_primary_future_path": True,
    }


def _blocked_cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "missing_scope_keys",
            "retrieval_allowed": False,
            "reason": "user_workspace_surface_retention_scope_required",
        },
        {
            "case_id": "raw_transcript_only_query",
            "retrieval_allowed": False,
            "reason": "summary_first_context_or_source_ref_required",
        },
        {
            "case_id": "stale_conflicting_memory",
            "retrieval_allowed": False,
            "recommended_action": "downgrade_or_human_review",
            "reason": "freshness_and_contradiction_review_required",
        },
        {
            "case_id": "proactive_low_precision_trigger",
            "retrieval_allowed": False,
            "recommended_action": "stay_silent_and_collect_more_evidence",
            "reason": "intelligent_proactive_requires_high_precision",
        },
    ]


def _product_capability_value() -> dict[str, str]:
    return {
        "recommendation": "retrieves preference, negative preference, and golden-order context without replacing FoodDB truth.",
        "intake_clarification": "retrieves user phrase and correction history to ask fewer, sharper questions.",
        "chat_context": "supports prior-topic recall through a future tool instead of prompt-dumping history.",
        "calibration": "retrieves logging quality and estimation-bias signals without changing calibration math.",
        "proactive": "prioritizes high-precision retrieval and silence when confidence is weak.",
        "rescue_later": "retrieves adherence and overshoot summaries only after current budget truth exists.",
    }


__all__ = ["_retrieval_ranking_policy_shadow_artifact"]
