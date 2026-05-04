from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.memory_extraction_lanes import (
    memory_extraction_lanes,
)


def _memory_extraction_storage_rag_artifact(
    fixture: dict[str, Any],
) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="memory_extraction_storage_rag_shadow_plan",
        fixture=fixture,
        extra={
            "external_framework_adopted_as_canonical": False,
            "repo_specs_remain_source_of_truth": True,
            "source_references_checked": _source_references_checked(),
            "raw_vs_canonical_policy": _raw_vs_canonical_policy(),
            "storage_zones": _storage_zones(),
            "extraction_lanes": memory_extraction_lanes(),
            "retrieval_and_rag_policy": _retrieval_and_rag_policy(),
            "product_capability_fit": _product_capability_fit(),
            "blocked_runtime_dependencies": _blocked_runtime_dependencies(),
            "external_reference_translation": _external_reference_translation(),
            "reference_recommendations": _reference_recommendations(),
        },
    )


def _source_references_checked() -> list[str]:
    return [
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


def _raw_vs_canonical_policy() -> dict[str, bool]:
    return {
        "raw_user_input_kept_as_evidence_only": True,
        "meal_thread_is_canonical_meal_truth": True,
        "fooddb_is_canonical_nutrition_truth": True,
        "memory_may_reference_but_not_replace_canonical_objects": True,
        "derived_memory_candidates_require_source_refs": True,
        "confirmed_memory_requires_human_review": True,
    }


def _storage_zones() -> list[dict[str, Any]]:
    return [
        {
            "store_id": "raw_trace_archive",
            "stores_raw_user_input": True,
            "stores_runtime_truth": False,
            "runtime_truth_owner": "trace_system",
            "write_allowed_now": False,
            "retrieval_use": "evidence_backlink_only",
        },
        {
            "store_id": "canonical_product_store",
            "stores_raw_user_input": False,
            "stores_runtime_truth": True,
            "runtime_truth_owner": "MealThread_FoodDB_BodyBudget",
            "write_allowed_now": False,
            "retrieval_use": "canonical_source_ref_resolution",
        },
        {
            "store_id": "derived_memory_candidate_store",
            "stores_raw_user_input": False,
            "stores_runtime_truth": False,
            "runtime_truth_owner": "shadow_lab",
            "write_allowed_now": True,
            "retrieval_use": "review_queue_and_shadow_context_pack",
        },
        {
            "store_id": "reviewed_memory_store_future",
            "stores_raw_user_input": False,
            "stores_runtime_truth": False,
            "runtime_truth_owner": "future_human_reviewed_memory",
            "write_allowed_now": False,
            "retrieval_use": "future_confirmed_memory_source",
        },
        {
            "store_id": "retrieval_index_future",
            "stores_raw_user_input": False,
            "stores_runtime_truth": False,
            "runtime_truth_owner": "future_memory_retrieval_adapter",
            "index_build_allowed_now": False,
            "write_allowed_now": False,
            "retrieval_use": "future_metadata_hybrid_search",
        },
        {
            "store_id": "audit_change_history",
            "stores_raw_user_input": False,
            "stores_runtime_truth": False,
            "runtime_truth_owner": "future_memory_governance",
            "write_allowed_now": False,
            "retrieval_use": "promotion_demotion_deletion_audit",
        },
    ]


def _retrieval_and_rag_policy() -> dict[str, Any]:
    return {
        "rag_is_not_default_memory_architecture": True,
        "deterministic_state_read_before_search": True,
        "metadata_filter_before_vector_search": True,
        "keyword_or_structured_filter_before_semantic_search": True,
        "summary_first_context_pack_required": True,
        "source_refs_required": True,
        "freshness_and_staleness_required": True,
        "negative_preferences_loaded_as_blocking_signals": True,
        "raw_full_history_dump_allowed": False,
        "active_runtime_tool_registered": False,
        "live_embedding_or_provider_call_allowed": False,
        "consumer_specific_retrieval_budgets": {
            "recommendation": "medium",
            "intake_clarification": "small",
            "chat_context": "small",
            "calibration": "structured_state_only",
            "proactive": "very_small_high_precision",
            "rescue_later": "medium_with_current_budget_required",
        },
    }


def _product_capability_fit() -> dict[str, str]:
    return {
        "recommendation": "rank, block, and explain choices from reviewed memory",
        "intake_clarification": "understand user phrases and choose fewer questions",
        "calibration": "attribute logging quality and estimation bias without math writes",
        "proactive": "suppress annoying sends and identify high-value quiet nudges",
        "rescue_later": "reuse adherence and overshoot history for proposal viability",
        "chat_context": "adapt response style and recall prior topics through tools",
    }


def _blocked_runtime_dependencies() -> list[str]:
    return [
        "durable_memory_schema_or_store",
        "embedding_or_hybrid_retrieval_index",
        "manager_context_retrieval_tool",
        "user_visible_memory_review_surface",
        "runtime_context_pack_injection_contract",
        "live_provider_extraction_eval",
    ]


def _external_reference_translation() -> list[dict[str, str]]:
    return [
        {
            "reference": "claude_code_official_memory",
            "adopt": "bounded memory entrypoint plus on-demand topic recall",
            "reject_or_defer": "always-loading large raw memory files",
        },
        {
            "reference": "openclaw_public_memory_docs",
            "adopt": "pre-promotion review lanes, backfill, freshness, contradiction",
            "reject_or_defer": "automatic runtime memory flush or live recall injection",
        },
        {
            "reference": "hermes_public_memory_provider_docs",
            "adopt": "provider lifecycle vocabulary and profile isolation pressure",
            "reject_or_defer": "provider plugin activation and post-turn sync hooks",
        },
        {
            "reference": "local_agent_runtime_skills",
            "adopt": "future utility, novelty, factuality, safety gates",
            "reject_or_defer": "automatic memory_add or memory_update operations",
        },
    ]


def _reference_recommendations() -> list[dict[str, str]]:
    return [
        {
            "reference": "openai_agents_sessions",
            "adopt": "explicit session scope and transcript-vs-memory separation",
            "defer": "",
            "reject": "treating full session history as automatic memory",
        },
        {
            "reference": "openai_agents_guardrails",
            "adopt": "tripwire-style activation guards before runtime use",
            "defer": "",
            "reject": "shadow guard output as runtime permission",
        },
        {
            "reference": "langgraph_memory_concepts",
            "adopt": "short-term vs long-term and semantic/episodic/procedural review vocabulary",
            "defer": "",
            "reject": "replacing L4A memory taxonomy",
        },
        {
            "reference": "local_hindsight_docs",
            "adopt": "",
            "defer": "hybrid semantic/keyword/graph/temporal retrieval until store/index gates exist",
            "reject": "early graph/vector index in this shadow PR",
        },
    ]


__all__ = ["_memory_extraction_storage_rag_artifact"]
