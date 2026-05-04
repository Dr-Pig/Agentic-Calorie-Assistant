from __future__ import annotations

from pathlib import Path


def test_local_framework_review_maps_framework_patterns_without_runtime_dependency(
    tmp_path: Path,
) -> None:
    hermes_doc = tmp_path / "hermes.md"
    openclaw_manifest = tmp_path / "openclaw.plugin.json"
    mem0_doc = tmp_path / "mem0_openclaw.mdx"

    hermes_doc.write_text(
        "Auto-recall via pre_llm_call. Auto-retain via post_llm_call. memory_mode hybrid/tools/context.",
        encoding="utf-8",
    )
    openclaw_manifest.write_text(
        '{"id":"hindsight-openclaw","kind":"memory","configSchema":{"properties":{"recallInjectionPosition":{},"llmApiKey":{}}}}',
        encoding="utf-8",
    )
    mem0_doc.write_text(
        "userId scopes memories. Auto-Capture after each response. Agent Tools memory_search memory_add.",
        encoding="utf-8",
    )

    from app.memory.application.local_memory_framework_review import (
        build_local_framework_review,
    )

    review = build_local_framework_review(tmp_path)

    assert review["artifact_type"] == "local_memory_framework_review"
    assert review["shadow_mode"] is True
    assert review["real_runtime_effect"] is False
    assert review["new_dependency_introduced"] is False
    assert review["local_framework_root"] == str(tmp_path)
    assert {item["framework_id"] for item in review["framework_reviews"]} >= {
        "hermes",
        "openclaw",
        "mem0",
    }
    assert any(
        "scope" in pattern
        for item in review["framework_reviews"]
        for pattern in item["adoptable_patterns"]
    )
    assert any(
        "auto-recall" in risk.lower()
        for item in review["framework_reviews"]
        for risk in item["rejected_or_deferred_patterns"]
    )
