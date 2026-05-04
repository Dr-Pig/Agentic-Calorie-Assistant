from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_external_reference_review_covers_current_agent_memory_practices() -> None:
    from app.memory.application.external_memory_framework_research import (
        build_external_memory_framework_research,
    )

    artifact = build_external_memory_framework_research(
        generated_at_utc="2026-05-05T00:00:00+08:00"
    )

    source_ids = {source["source_id"] for source in artifact["research_sources"]}
    assert {
        "openai-agents-sessions",
        "openai-agents-agent-memory",
        "openai-agents-guardrails",
        "langgraph-memory-concepts",
        "local-hindsight-memory-docs",
    }.issubset(source_ids)

    for source in artifact["research_sources"]:
        assert source["shadow_lab_translation"]
        assert source["product_capability_helped"]
        assert source["adopt_defer_or_reject"] in {"adopt", "defer", "reject"}
        assert source["risk_if_misapplied"]


def test_memory_rag_plan_recommends_references_without_superseding_repo_specs() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "memory_extraction_storage_rag_shadow_plan"
    ]

    refs = set(artifact["source_references_checked"])
    assert {
        "docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md",
        "https://openai.github.io/openai-agents-python/sessions/",
        "https://openai.github.io/openai-agents-python/sandbox/memory/",
        "https://openai.github.io/openai-agents-python/guardrails/",
        "https://docs.langchain.com/oss/python/concepts/memory",
        "local_hindsight_docs_read_only",
    }.issubset(refs)

    recommendations = {
        item["reference"]: item for item in artifact["reference_recommendations"]
    }
    assert recommendations["openai_agents_sessions"]["adopt"]
    assert recommendations["openai_agents_guardrails"]["adopt"]
    assert recommendations["langgraph_memory_concepts"]["adopt"]
    assert recommendations["local_hindsight_docs"]["defer"]

    assert artifact["external_framework_adopted_as_canonical"] is False
    assert artifact["repo_specs_remain_source_of_truth"] is True
