from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow_lab import (
    SHADOW_NON_CLAIM_FLAGS,
    artifact_review_contract,
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
        **SHADOW_NON_CLAIM_FLAGS,
        **artifact_review_contract("external_memory_framework_research_review"),
        "research_sources": _research_sources(),
        "adopted_design_pressure": _adopted_design_pressure(),
        "deferred_patterns": _deferred_patterns(),
        "product_translation": _product_translation(),
    }


def _research_sources() -> list[dict[str, Any]]:
    return [
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
    ]


def _adopted_design_pressure() -> list[str]:
    return [
        "Keep memory provider/context engine seams separate from product truth.",
        "Represent lifecycle hooks as explicit future activation points.",
        "Preserve provenance, freshness, contradiction risk, and omission traces.",
        "Prefer summary-first compiled context packs over raw conversation dumps.",
        "Treat conversation recall as tool-mediated retrieval with scope and review.",
        "Use review lanes before any promotion into confirmed or durable memory.",
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
