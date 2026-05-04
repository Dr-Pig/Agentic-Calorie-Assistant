from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow_lab import (
    SHADOW_NON_CLAIM_FLAGS,
    artifact_review_contract,
)
from app.memory.application.external_memory_reference_catalog import (
    current_agent_memory_reference_sources,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.external_memory_framework_research"
)


def build_external_memory_framework_research(
    *,
    generated_at_utc: str,
) -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "external_memory_framework_research_review",
        "status": "generated",
        "generated_at_utc": generated_at_utc,
        "claim_scope": "external_framework_research_review_only",
        "local_only": True,
        "diagnostic_only": True,
        "live_provider_called": False,
        "network_access_used_by_builder": False,
        "new_dependency_introduced": False,
        "external_framework_adopted_as_canonical": False,
        "l4a_l4c_superseded": False,
        "legal_source_policy": {
            "claude_code_leaked_source_used": False,
            "public_docs_only_for_claude_code": True,
            "local_skills_read_only": True,
            "external_frameworks_not_canonical": True,
        },
        **SHADOW_NON_CLAIM_FLAGS,
        **artifact_review_contract("external_memory_framework_research_review"),
        "research_sources": _research_sources(),
        "adopted_design_pressure": _adopted_design_pressure(),
        "deferred_patterns": _deferred_patterns(),
        "product_translation": _product_translation(),
    }


def _research_sources() -> list[dict[str, Any]]:
    sources = [
        {
            "source_id": "claude-code-official-memory-docs",
            "framework_id": "claude_code",
            "source_kind": "official_docs",
            "source_url": "https://code.claude.com/docs/en/memory",
            "observed_practices": [
                "memory_files_loaded_with_scope_order",
                "modular_rules_loaded_by_path_scope",
                "on_demand_topic_memory_files",
                "memory_index_size_limit",
                "plain_text_auditable_memory",
            ],
            "shadow_lab_translation": (
                "Use bounded memory entrypoints and on-demand topic recall as "
                "context packing pressure; do not read leaked source code."
            ),
        },
        {
            "source_id": "claude-memory-tool-official-guidance",
            "framework_id": "claude_code",
            "source_kind": "official_docs",
            "source_url": (
                "https://platform.claude.com/docs/en/agents-and-tools/"
                "tool-use/memory-tool"
            ),
            "observed_practices": [
                "memory_file_size_limits",
                "paginated_memory_reading",
                "memory_expiration",
                "bounded_memory_tool_output",
            ],
            "shadow_lab_translation": (
                "Adopt file-size, pagination, and expiration constraints as "
                "future memory review requirements."
            ),
        },
        {
            "source_id": "hermes-memory-providers-user-guide",
            "framework_id": "hermes",
            "source_kind": "official_docs",
            "source_url": (
                "https://hermes-agent.nousresearch.com/docs/user-guide/features/"
                "memory-providers"
            ),
            "observed_practices": [
                "single_active_external_memory_provider",
                "provider_context_injection",
                "background_prefetch_before_turn",
                "conversation_sync_after_response",
                "session_end_memory_extraction",
                "provider_specific_memory_tools",
            ],
            "shadow_lab_translation": (
                "Represent provider lifecycle as future activation modes while all "
                "context injection and memory writes stay disabled."
            ),
        },
        {
            "source_id": "hermes-memory-provider-plugin-guide",
            "framework_id": "hermes",
            "source_kind": "official_docs",
            "source_url": (
                "https://hermes-agent.nousresearch.com/docs/developer-guide/"
                "memory-provider-plugin/"
            ),
            "observed_practices": [
                "provider_availability_check_without_network_calls",
                "prefetch_hook",
                "queue_prefetch_hook",
                "sync_turn_hook",
                "pre_compress_hook",
                "built_in_memory_write_mirroring",
            ],
            "shadow_lab_translation": (
                "Keep hook vocabulary as review metadata only; do not register a "
                "provider or lifecycle hook."
            ),
        },
        {
            "source_id": "hermes-release-pluggable-memory-provider",
            "framework_id": "hermes",
            "source_kind": "release_notes",
            "source_url": "https://github.com/NousResearch/hermes-agent/releases",
            "observed_practices": [
                "pluggable_memory_provider_interface",
                "profile_isolation",
                "memory_flush_state_persistence",
                "memory_provider_tool_sequential_execution",
            ],
            "shadow_lab_translation": (
                "Use profile/scope isolation and sequential review semantics as "
                "future design pressure, not runtime integration."
            ),
        },
        {
            "source_id": "openclaw-memory-concepts",
            "framework_id": "openclaw",
            "source_kind": "source_repo_docs",
            "source_url": (
                "https://github.com/openclaw/openclaw/blob/main/docs/concepts/memory.md"
            ),
            "observed_practices": [
                "memory_search_tool",
                "hybrid_vector_keyword_search",
                "deterministic_memory_wiki_structure",
                "structured_claims_and_evidence",
                "freshness_and_contradiction_tracking",
                "compiled_runtime_digests",
                "automatic_pre_compaction_memory_flush",
                "opt_in_thresholded_dreaming_promotion",
                "reviewable_dream_diary",
                "grounded_backfill_review_lane",
            ],
            "shadow_lab_translation": (
                "Adopt provenance, freshness, omission traces, review lanes, and "
                "future tool-mediated retrieval as shadow artifacts only."
            ),
        },
        {
            "source_id": "openclaw-memory-search-docs",
            "framework_id": "openclaw",
            "source_kind": "official_docs",
            "source_url": "https://docs.openclaw.ai/concepts/memory-search",
            "observed_practices": [
                "configurable_embedding_provider",
                "local_embedding_option",
                "memory_index_status_checks",
                "hybrid_index_troubleshooting",
            ],
            "shadow_lab_translation": (
                "Use provider/index status as future diagnostics only; do not "
                "activate embeddings or memory search in this PR."
            ),
        },
        {
            "source_id": "local-agent-runtime-memory-skills",
            "framework_id": "local_agent_runtime_skills",
            "source_kind": "local_read_only_skills",
            "source_url": "local://C:/Users/User/Desktop/agent runtime",
            "observed_practices": [
                "future_utility_gate",
                "novelty_gate",
                "factuality_gate",
                "safety_secret_gate",
                "retain_raw_content_with_context",
                "stable_document_id",
                "tag_scope_before_recall",
                "consolidation_delete_merge_rewrite",
            ],
            "shadow_lab_translation": (
                "Adopt the quality gates and scope/tag discipline as artifact "
                "policy; defer automatic memory tool writes."
            ),
        },
    ]
    sources.extend(current_agent_memory_reference_sources())
    return [_with_reference_review_fields(source) for source in sources]


def _with_reference_review_fields(source: dict[str, Any]) -> dict[str, Any]:
    reviewed = dict(source)
    reviewed.setdefault("product_capability_helped", "architecture_governance")
    reviewed.setdefault("adopt_defer_or_reject", "adopt")
    reviewed.setdefault(
        "risk_if_misapplied",
        "Could over-adopt framework behavior before repo L4A/L4C/L4D review.",
    )
    return reviewed


def _adopted_design_pressure() -> list[str]:
    return [
        "Keep memory provider/context engine seams separate from product truth.",
        "Represent lifecycle hooks as explicit future activation points.",
        "Preserve provenance, freshness, contradiction risk, and omission traces.",
        "Prefer summary-first compiled context packs over raw conversation dumps.",
        "Treat conversation recall as tool-mediated retrieval with scope and review.",
        "Use review lanes before any promotion into confirmed or durable memory.",
        "local_skill_future_utility_gate",
        "local_skill_safety_secret_gate",
        "stable_document_id_for_raw_trace_retention",
        "metadata_scope_before_semantic_retrieval",
    ]


def _deferred_patterns() -> list[str]:
    return [
        "provider_context_auto_injection",
        "background_prefetch_before_each_turn",
        "post_response_conversation_sync",
        "session_end_memory_extraction",
        "memory_provider_tool_registration",
        "embedding_provider_auto_detection",
        "live_hybrid_search",
        "automatic_memory_flush_or_dreaming_promotion",
        "compiled_digest_loading_into_runtime",
        "leaked_claude_code_source_or_zip_review",
        "automatic_memory_add",
        "automatic_memory_update",
        "post_response_auto_capture",
    ]


def _product_translation() -> dict[str, str]:
    return {
        "food_preference_memory": (
            "Prioritize recommendation defaults and golden-order review while "
            "keeping FoodDB and MealThread canonical."
        ),
        "user_language_memory": (
            "Capture user-specific phrases and aliases for future intake "
            "clarification, not automatic food truth."
        ),
        "estimation_bias_memory": (
            "Feed calibration confidence and attribution review, never direct "
            "calorie truth rewrites."
        ),
        "app_usage_style_memory": (
            "Capture response and reminder style candidates for future chat and "
            "proactive personalization."
        ),
        "conversation_recall_context": (
            "Treat prior conversation lookup as future manager tool-mediated retrieval, "
            "not as durable memory auto-injection."
        ),
    }


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_external_memory_framework_research",
]
