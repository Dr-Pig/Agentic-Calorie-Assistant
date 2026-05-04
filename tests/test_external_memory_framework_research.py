from __future__ import annotations


def test_external_framework_research_records_current_best_practices_without_runtime_use() -> (
    None
):
    from app.memory.application.external_memory_framework_research import (
        build_external_memory_framework_research,
    )

    review = build_external_memory_framework_research(
        generated_at_utc="2026-05-04T00:00:00+00:00"
    )

    assert review["artifact_type"] == "external_memory_framework_research_review"
    assert review["shadow_mode"] is True
    assert review["real_runtime_effect"] is False
    assert review["live_provider_called"] is False
    assert review["network_access_used_by_builder"] is False
    assert review["external_framework_adopted_as_canonical"] is False
    assert {source["framework_id"] for source in review["research_sources"]} == {
        "claude_code",
        "openai_agents",
        "langgraph",
        "hermes",
        "openclaw",
        "hindsight",
        "local_agent_runtime_skills",
    }
    assert review["legal_source_policy"] == {
        "claude_code_leaked_source_used": False,
        "public_docs_only_for_claude_code": True,
        "local_skills_read_only": True,
        "external_frameworks_not_canonical": True,
    }
    assert any(
        source["source_url"].startswith("https://code.claude.com/docs/en/memory")
        for source in review["research_sources"]
    )
    assert any(
        source["source_url"].startswith("https://hermes-agent.nousresearch.com/docs/")
        for source in review["research_sources"]
    )
    assert any(
        source["source_url"].startswith("https://github.com/openclaw/openclaw/")
        for source in review["research_sources"]
    )
    assert "provider_context_auto_injection" in review["deferred_patterns"]
    assert "automatic_memory_flush_or_dreaming_promotion" in review["deferred_patterns"]
    assert "leaked_claude_code_source_or_zip_review" in review["deferred_patterns"]
    assert "local_skill_future_utility_gate" in review["adopted_design_pressure"]
    assert review["product_translation"]["conversation_recall_context"] == (
        "Treat prior conversation lookup as future manager tool-mediated retrieval, "
        "not as durable memory auto-injection."
    )
