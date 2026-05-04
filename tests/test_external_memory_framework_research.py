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
        "hermes",
        "openclaw",
    }
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
    assert review["product_translation"]["conversation_recall_context"] == (
        "Treat prior conversation lookup as future manager tool-mediated retrieval, "
        "not as durable memory auto-injection."
    )
