from __future__ import annotations

from typing import Any


def current_agent_memory_reference_sources() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "openai-agents-sessions",
            "framework_id": "openai_agents",
            "source_kind": "official_docs",
            "source_url": "https://openai.github.io/openai-agents-python/sessions/",
            "observed_practices": [
                "session_history_is_separate_from_long_term_memory",
                "multiple_session_backends",
                "conversation_continuity_requires_explicit_session_scope",
            ],
            "product_capability_helped": "chat_context",
            "adopt_defer_or_reject": "adopt",
            "risk_if_misapplied": "Could treat session transcript as confirmed memory.",
            "shadow_lab_translation": (
                "Keep conversation recall as scoped context ingress, not automatic "
                "durable memory."
            ),
        },
        {
            "source_id": "openai-agents-agent-memory",
            "framework_id": "openai_agents",
            "source_kind": "official_docs",
            "source_url": "https://openai.github.io/openai-agents-python/sandbox/memory/",
            "observed_practices": [
                "distilled_reusable_memory",
                "background_memory_processing",
                "memory_records_are_separate_from_raw_session_items",
            ],
            "product_capability_helped": "memory_governance",
            "adopt_defer_or_reject": "adopt",
            "risk_if_misapplied": "Could write distilled memory before review.",
            "shadow_lab_translation": (
                "Use distilled-memory vocabulary for future storage design while "
                "keeping writes disabled in shadow mode."
            ),
        },
        {
            "source_id": "openai-agents-guardrails",
            "framework_id": "openai_agents",
            "source_kind": "official_docs",
            "source_url": "https://openai.github.io/openai-agents-python/guardrails/",
            "observed_practices": [
                "input_guardrails",
                "output_guardrails",
                "tripwire_result",
                "guardrail_context",
            ],
            "product_capability_helped": "runtime_boundary_governance",
            "adopt_defer_or_reject": "adopt",
            "risk_if_misapplied": "Could make shadow guard output look like runtime approval.",
            "shadow_lab_translation": (
                "Model no-runtime-effect checks as guardrail tripwires before any "
                "future memory activation."
            ),
        },
        {
            "source_id": "langgraph-memory-concepts",
            "framework_id": "langgraph",
            "source_kind": "official_docs",
            "source_url": "https://docs.langchain.com/oss/python/concepts/memory",
            "observed_practices": [
                "short_term_vs_long_term_memory",
                "semantic_episodic_procedural_memory",
                "hot_path_vs_background_memory_writes",
            ],
            "product_capability_helped": "memory_layering",
            "adopt_defer_or_reject": "adopt",
            "risk_if_misapplied": "Could over-generalize framework taxonomy over L4A.",
            "shadow_lab_translation": (
                "Use as a cross-check for L4A layers; do not replace repo memory "
                "taxonomy."
            ),
        },
        {
            "source_id": "local-hindsight-memory-docs",
            "framework_id": "hindsight",
            "source_kind": "local_read_only_docs",
            "source_url": "local://C:/Users/User/Desktop/agent runtime/memory/hindsight-main",
            "observed_practices": [
                "semantic_keyword_graph_temporal_retrieval",
                "reciprocal_rank_fusion",
                "source_chunk_fallback",
                "token_budgeted_recall",
            ],
            "product_capability_helped": "future_memory_retrieval",
            "adopt_defer_or_reject": "defer",
            "risk_if_misapplied": "Could introduce graph/vector infrastructure too early.",
            "shadow_lab_translation": (
                "Keep multi-strategy recall as future retrieval design pressure; "
                "do not build an index in this PR."
            ),
        },
    ]


__all__ = ["current_agent_memory_reference_sources"]
