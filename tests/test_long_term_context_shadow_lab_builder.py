from __future__ import annotations

import json
from pathlib import Path

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_shadow_lab_builder_script_writes_all_artifacts(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixture.json"
    output_dir = tmp_path / "artifacts"
    fixture_path.write_text(
        json.dumps(_fixture_payload(), ensure_ascii=False), encoding="utf-8"
    )

    from scripts.build_long_term_context_shadow_lab import main

    exit_code = main(
        ["--fixture-json", str(fixture_path), "--output-dir", str(output_dir)]
    )

    assert exit_code == 0
    expected_files = {
        "artifact_registry_manifest.json",
        "long_term_memory_candidate_review.json",
        "context_value_review_queue.json",
        "proactive_no_send_simulation.json",
        "recommendation_shadow_eval.json",
        "rescue_shadow_candidates.json",
        "memory_review_action_shadow_result.json",
        "conversation_recall_shadow_eval.json",
        "long_term_context_pack_shadow_eval.json",
        "conversation_recall_tool_shadow_plan.json",
        "context_ingress_decision_shadow_eval.json",
        "memory_extraction_storage_rag_shadow_plan.json",
        "retrieval_ranking_policy_shadow_eval.json",
        "manager_memory_contract_shadow_plan.json",
        "pre_compaction_memory_flush_shadow_plan.json",
        "memory_do_not_save_policy_shadow_eval.json",
        "product_capability_context_map.json",
        "memory_dependency_graph_shadow_eval.json",
        "memory_promotion_demotion_shadow_eval.json",
        "semantic_pattern_extraction_shadow_plan.json",
        "context_signal_quality_scorecard.json",
        "context_pack_token_pressure_shadow_eval.json",
        "conversation_recall_retrieval_shadow_eval.json",
        "entity_normalization_shadow_plan.json",
        "context_quality_contradiction_review_queue.json",
        "capability_scenario_fixture_pack.json",
        "pr_review_autopilot_closeout.json",
        "candidate_extraction_engine_v2.json",
        "derived_memory_views_shadow_eval.json",
        "context_signal_lifecycle_shadow_eval.json",
        "user_context_profile_shadow_eval.json",
        "scope_isolation_shadow_eval.json",
        "proactive_intelligence_shadow_eval.json",
        "contextual_friction_budget_shadow_eval.json",
        "menu_highlight_shadow_eval.json",
        "consumer_memory_substrate_shadow_eval.json",
        "context_value_scoring_v2.json",
        "shadow_replay_evaluators.json",
        "review_queue_reducer.json",
        "external_memory_framework_research_review.json",
    }
    assert {path.name for path in output_dir.iterdir()} == expected_files
    manifest = json.loads(
        (output_dir / "artifact_registry_manifest.json").read_text(encoding="utf-8")
    )
    manifest_entries = {
        entry["artifact_key"] for entry in manifest["artifact_registry_entries"]
    }
    assert manifest["artifact_count"] == len(expected_files)
    assert "external_memory_framework_research_review" in manifest_entries
    assert manifest["artifacts_without_consumers"] == []
    assert manifest["pseudo_runtime_truth_risks"] == []
    for path in output_dir.iterdir():
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["shadow_mode"] is True
        assert payload["real_runtime_effect"] is False


def test_shadow_lab_builder_script_writes_local_deep_review_when_root_is_present(
    tmp_path: Path,
) -> None:
    fixture_path = tmp_path / "fixture.json"
    output_dir = tmp_path / "artifacts"
    framework_root = tmp_path / "frameworks"
    framework_root.mkdir()
    (framework_root / "openclaw_memory.md").write_text(
        "scope recallInjectionPosition contradiction freshness review",
        encoding="utf-8",
    )
    fixture_path.write_text(
        json.dumps(_fixture_payload(), ensure_ascii=False), encoding="utf-8"
    )

    from scripts.build_long_term_context_shadow_lab import main

    exit_code = main(
        [
            "--fixture-json",
            str(fixture_path),
            "--output-dir",
            str(output_dir),
            "--local-framework-root",
            str(framework_root),
        ]
    )

    assert exit_code == 0
    assert (output_dir / "local_memory_framework_review.json").exists()
    assert (output_dir / "local_memory_framework_deep_review.json").exists()
    manifest = json.loads(
        (output_dir / "artifact_registry_manifest.json").read_text(encoding="utf-8")
    )
    manifest_entries = {
        entry["artifact_key"] for entry in manifest["artifact_registry_entries"]
    }
    assert "local_memory_framework_deep_review" in manifest_entries
    assert manifest["artifacts_without_consumers"] == []
    assert manifest["pseudo_runtime_truth_risks"] == []
