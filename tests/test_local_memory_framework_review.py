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


def test_local_framework_deep_review_scores_fit_without_adopting_runtime(
    tmp_path: Path,
) -> None:
    hermes_doc = tmp_path / "hermes_memory.md"
    openclaw_doc = tmp_path / "openclaw_memory.md"
    graphiti_doc = tmp_path / "graphiti_memory.md"

    hermes_doc.write_text(
        "pre_llm_call post_llm_call memory_mode provider sync conversation memory",
        encoding="utf-8",
    )
    openclaw_doc.write_text(
        "scope recallInjectionPosition review backfill contradiction freshness entity",
        encoding="utf-8",
    )
    graphiti_doc.write_text(
        "graph entity temporal provenance search retrieval",
        encoding="utf-8",
    )

    from app.memory.application.local_memory_framework_review import (
        build_local_framework_deep_review,
    )

    review = build_local_framework_deep_review(tmp_path)

    assert review["artifact_type"] == "local_memory_framework_deep_review"
    assert review["shadow_mode"] is True
    assert review["read_only_review"] is True
    assert review["new_dependency_introduced"] is False
    assert review["runtime_integration_recommended"] is False
    assert review["runtime_effect_allowed"] is False
    assert review["review_questions"] == [
        "raw_history_vs_derived_vs_confirmed_memory",
        "promotion_and_demotion_policy",
        "provenance_and_source_refs",
        "freshness_and_staleness",
        "prompt_pollution_prevention",
        "retrieval_ranking_and_scope",
        "user_correction_deletion_suppression",
        "no_send_proactive_simulation",
    ]
    assert {item["framework_id"] for item in review["framework_scorecards"]} >= {
        "hermes",
        "openclaw",
        "graphiti",
    }
    assert all(
        scorecard["runtime_effect_allowed"] is False
        for scorecard in review["framework_scorecards"]
    )
    assert "provider_context_auto_injection" in review["global_deferred_patterns"]


def test_local_deep_review_includes_memory_skill_patterns_without_running_tools(
    tmp_path: Path,
) -> None:
    skill_dir = tmp_path / "memory" / "openclaw" / "skills" / "memory-triage"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "future utility novelty factual safe credentials memory_add memory_search",
        encoding="utf-8",
    )
    docs_dir = tmp_path / "memory" / "hindsight" / "skills" / "hindsight-docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "best-practices.md").write_text(
        "Retain raw content with context document_id timestamp tags recall budget",
        encoding="utf-8",
    )

    from app.memory.application.local_memory_framework_review import (
        build_local_framework_deep_review,
    )

    review = build_local_framework_deep_review(tmp_path)
    summary = review["local_skill_reference_summary"]

    assert summary["read_only_review"] is True
    assert summary["tool_or_provider_started"] is False
    assert summary["skill_files_reviewed"] >= 2
    assert {
        "future_utility_gate",
        "novelty_gate",
        "factuality_gate",
        "safety_secret_gate",
        "stable_document_id",
        "tag_scope_before_recall",
    }.issubset(set(summary["adopted_skill_patterns"]))
    assert "automatic_memory_add" in summary["deferred_skill_patterns"]
    assert summary["product_translation"]["raw_input"] == (
        "retain as evidence with context, timestamp, and source refs"
    )
