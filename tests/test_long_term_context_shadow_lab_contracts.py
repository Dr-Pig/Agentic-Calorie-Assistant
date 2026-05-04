from __future__ import annotations

import json

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_shadow_lab_builds_review_artifacts_with_required_non_claim_flags() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        SHADOW_NON_CLAIM_FLAGS,
        build_shadow_lab_artifacts,
    )

    artifacts = build_shadow_lab_artifacts(_fixture_payload())

    assert set(artifacts) == {
        "artifact_registry_manifest",
        "long_term_memory_candidate_review",
        "context_value_review_queue",
        "proactive_no_send_simulation",
        "recommendation_shadow_eval",
        "rescue_shadow_candidates",
        "memory_review_action_shadow_result",
        "conversation_recall_shadow_eval",
        "long_term_context_pack_shadow_eval",
        "conversation_recall_tool_shadow_plan",
        "context_ingress_decision_shadow_eval",
        "memory_extraction_storage_rag_shadow_plan",
        "retrieval_ranking_policy_shadow_eval",
        "manager_memory_contract_shadow_plan",
        "pre_compaction_memory_flush_shadow_plan",
        "memory_do_not_save_policy_shadow_eval",
        "product_capability_context_map",
        "memory_dependency_graph_shadow_eval",
        "memory_promotion_demotion_shadow_eval",
        "semantic_pattern_extraction_shadow_plan",
        "context_signal_quality_scorecard",
        "context_pack_token_pressure_shadow_eval",
        "conversation_recall_retrieval_shadow_eval",
        "entity_normalization_shadow_plan",
        "context_quality_contradiction_review_queue",
        "capability_scenario_fixture_pack",
        "pr_review_autopilot_closeout",
        "candidate_extraction_engine_v2",
        "derived_memory_views_shadow_eval",
        "context_signal_lifecycle_shadow_eval",
        "user_context_profile_shadow_eval",
        "scope_isolation_shadow_eval",
        "proactive_intelligence_shadow_eval",
        "contextual_friction_budget_shadow_eval",
        "menu_highlight_shadow_eval",
        "consumer_memory_substrate_shadow_eval",
        "context_value_scoring_v2",
        "shadow_replay_evaluators",
        "review_queue_reducer",
    }

    for artifact in artifacts.values():
        for key, expected in SHADOW_NON_CLAIM_FLAGS.items():
            assert artifact[key] is expected
        assert artifact["fixture_input_used"] is True
        assert artifact["real_dogfood_export_used"] is False
        assert artifact["runtime_effect_allowed"] is False
        assert artifact["intended_consumers"]
        assert artifact["consumer_use_hints"]
        assert artifact["risk_if_wrong"]
        assert artifact["promotion_path"]
        assert artifact["why_this_is_not_runtime_truth"]


def test_artifact_registry_manifest_indexes_every_artifact_contract() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifacts = build_shadow_lab_artifacts(_fixture_payload())
    manifest = artifacts["artifact_registry_manifest"]

    assert manifest["artifact_type"] == "artifact_registry_manifest"
    assert manifest["runtime_effect_allowed"] is False
    assert manifest["artifacts_without_consumers"] == []
    assert manifest["pseudo_runtime_truth_risks"] == []

    entries = {
        entry["artifact_key"]: entry for entry in manifest["artifact_registry_entries"]
    }
    assert set(entries) == set(artifacts)
    for artifact_key, artifact in artifacts.items():
        entry = entries[artifact_key]
        assert entry["artifact_type"] == artifact["artifact_type"]
        assert entry["intended_consumers"] == artifact["intended_consumers"]
        assert entry["consumer_use_hints"] == artifact["consumer_use_hints"]
        assert entry["risk_if_wrong"] == artifact["risk_if_wrong"]
        assert entry["promotion_path"] == artifact["promotion_path"]
        assert (
            entry["why_this_is_not_runtime_truth"]
            == artifact["why_this_is_not_runtime_truth"]
        )
        assert entry["runtime_effect_allowed"] is False
        assert entry["manager_context_injection_allowed"] is False


def test_expanded_dogfood_export_reader_normalizes_nested_export_sections() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    fixture = {
        "user_id": "fixture-user",
        "generated_at_utc": "2026-04-09T00:00:00+00:00",
        "dogfood_export": {
            "meal_logs": [
                {
                    "trace_id": "expanded-meal-1",
                    "meal_id": "expanded-m1",
                    "logged_at": "2026-04-07T08:00:00+08:00",
                    "item_names": ["oatmeal"],
                    "item_kinds": ["staple"],
                    "staple_types": ["oats"],
                    "drink_names": [],
                    "store_name": "Morning Bar",
                }
            ],
            "body_observations": [
                {
                    "trace_id": "expanded-body-1",
                    "observed_at": "2026-04-07T07:30:00+08:00",
                    "weight_kg": 81.9,
                }
            ],
            "budget_summaries": [
                {
                    "trace_id": "expanded-budget-1",
                    "date": "2026-04-07",
                    "target_kcal": 2100,
                    "actual_kcal": 2240,
                    "overshoot_kcal": 140,
                }
            ],
            "calibration_diagnostics": [
                {
                    "trace_id": "expanded-cal-1",
                    "window_start": "2026-03-30",
                    "window_end": "2026-04-07",
                    "expected_weight_delta_kg": -0.3,
                    "observed_weight_delta_kg": -0.1,
                }
            ],
            "chat_trace_metadata": [
                {
                    "trace_id": "expanded-chat-1",
                    "conversation_id": "chat-expanded",
                    "observed_at": "2026-04-07T23:00:00+08:00",
                    "summary": "User preferred fewer repeated follow-up questions.",
                    "topic_tags": ["followup_preference"],
                }
            ],
            "trace_metadata": [
                {
                    "trace_id": "expanded-meal-1",
                    "source_object_ref": "MealThread:expanded-m1",
                }
            ],
        },
    }

    review = build_shadow_lab_artifacts(fixture)["long_term_memory_candidate_review"]

    assert review["input_reader"]["source_shape"] == "dogfood_export"
    assert review["input_reader"]["real_dogfood_export_claim_ignored"] is True
    assert set(review["input_reader"]["normalized_sections"]) >= {
        "meal_logs",
        "body_observations",
        "budget_summaries",
        "calibration_diagnostics",
        "conversation_history_summaries",
        "trace_metadata",
    }
    candidate_types = {
        candidate["candidate_type"] for candidate in review["candidates"]
    }
    assert {
        "pattern",
        "logging_adherence_pattern",
        "conversation_recall_context",
    }.issubset(candidate_types)


def test_shadow_lab_forces_fixture_only_provenance_flags_even_if_input_claims_real_export() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    fixture = _fixture_payload()
    fixture["fixture_input_used"] = False
    fixture["real_dogfood_export_used"] = True

    artifacts = build_shadow_lab_artifacts(fixture)

    for artifact in artifacts.values():
        assert artifact["fixture_input_used"] is True
        assert artifact["real_dogfood_export_used"] is False


def test_shadow_lab_artifacts_are_stable_for_identical_fixture_input() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    first = build_shadow_lab_artifacts(_fixture_payload())
    second = build_shadow_lab_artifacts(_fixture_payload())

    assert first == second


def test_shadow_lab_redacts_secret_like_fixture_fields_before_claiming_scan_status() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    fixture = _fixture_payload()
    fixture["intake_estimation_events"][0]["api_key"] = "sk-secret-fixture"

    artifact = build_shadow_lab_artifacts(fixture)["long_term_memory_candidate_review"]
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert "sk-secret-fixture" not in serialized
    bias = next(
        candidate
        for candidate in artifact["candidates"]
        if candidate["candidate_type"] == "intake_estimation_bias"
    )
    assert bias["secret_scan"]["status"] == "redacted_secret_fields_detected"
    assert bias["secret_scan"]["redacted_fields"] == ["events[0].api_key"]


def test_shadow_lab_normalizes_mixed_timezone_fixture_datetimes() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    fixture = _fixture_payload()
    fixture["meal_logs"][0]["logged_at"] = "2026-04-01T08:15:00"
    fixture["meal_logs"][1]["logged_at"] = "2026-04-02T08:05:00+08:00"

    artifact = build_shadow_lab_artifacts(fixture)["long_term_memory_candidate_review"]

    golden_order = next(
        candidate
        for candidate in artifact["candidates"]
        if candidate["candidate_type"] == "golden_order"
    )
    assert golden_order["evidence_window_start"].endswith(("Z", "+00:00"))
    assert golden_order["evidence_window_end"].endswith(("Z", "+00:00"))
