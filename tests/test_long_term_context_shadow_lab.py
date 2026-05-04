from __future__ import annotations

import json
from pathlib import Path


def _fixture_payload() -> dict:
    return {
        "fixture_input_used": True,
        "real_dogfood_export_used": False,
        "user_id": "fixture-user",
        "meal_logs": [
            {
                "trace_id": "meal-1",
                "meal_id": "m1",
                "logged_at": "2026-04-01T08:15:00+08:00",
                "item_names": ["oatmeal", "latte"],
                "item_kinds": ["staple", "drink"],
                "staple_types": ["oats"],
                "drink_names": ["latte"],
                "store_name": "Morning Bar",
            },
            {
                "trace_id": "meal-2",
                "meal_id": "m2",
                "logged_at": "2026-04-02T08:05:00+08:00",
                "item_names": ["oatmeal", "latte"],
                "item_kinds": ["staple", "drink"],
                "staple_types": ["oats"],
                "drink_names": ["latte"],
                "store_name": "Morning Bar",
            },
            {
                "trace_id": "meal-3",
                "meal_id": "m3",
                "logged_at": "2026-04-03T08:22:00+08:00",
                "item_names": ["oatmeal", "latte"],
                "item_kinds": ["staple", "drink"],
                "staple_types": ["oats"],
                "drink_names": ["latte"],
                "store_name": "Morning Bar",
            },
            {
                "trace_id": "meal-4",
                "meal_id": "m4",
                "logged_at": "2026-04-04T21:20:00+08:00",
                "item_names": ["fried chicken"],
                "item_kinds": ["main"],
                "staple_types": [],
                "drink_names": [],
                "store_name": "Night Market",
            },
        ],
        "body_observations": [
            {
                "trace_id": "body-1",
                "observed_at": "2026-04-01T07:30:00+08:00",
                "weight_kg": 82.1,
            },
            {
                "trace_id": "body-2",
                "observed_at": "2026-04-08T07:35:00+08:00",
                "weight_kg": 81.8,
            },
        ],
        "budget_summaries": [
            {
                "trace_id": "budget-1",
                "date": "2026-04-01",
                "target_kcal": 2100,
                "actual_kcal": 2300,
                "overshoot_kcal": 200,
            },
            {
                "trace_id": "budget-2",
                "date": "2026-04-02",
                "target_kcal": 2100,
                "actual_kcal": 2000,
                "overshoot_kcal": 0,
            },
        ],
        "calibration_diagnostics": [
            {
                "trace_id": "cal-1",
                "window_start": "2026-03-25",
                "window_end": "2026-04-08",
                "expected_weight_delta_kg": -0.4,
                "observed_weight_delta_kg": -0.1,
            }
        ],
        "language_observations": [
            {
                "trace_id": "lang-1",
                "observed_at": "2026-04-02T12:20:00+08:00",
                "user_phrase": "正常便當",
                "observed_meaning": "usually rice, one main, and two to three sides",
                "phrase_kind": "portion_phrase",
                "portion_semantics": {
                    "portion_label": "normal_meal",
                    "expected_components": ["rice", "main", "two_to_three_sides"],
                },
                "confidence": 0.62,
            }
        ],
        "intake_estimation_events": [
            {
                "trace_id": "bias-1",
                "observed_at": "2026-04-03T22:15:00+08:00",
                "bias_direction": "likely_underestimate",
                "event_kind": "missed_item_pattern",
                "reason": "missed_drink_or_sauce",
                "missed_item_kind": "drink_or_sauce",
                "correction_tendency": "adds_kcal_after_clarification",
                "correction_delta_kcal": 180,
            }
        ],
        "app_usage_events": [
            {
                "trace_id": "usage-1",
                "observed_at": "2026-04-04T23:10:00+08:00",
                "usage_signal": "late_night_backfill",
                "surface": "chat",
            },
            {
                "trace_id": "usage-2",
                "observed_at": "2026-04-05T09:10:00+08:00",
                "usage_signal": "accepted_quick_action",
                "surface": "chat",
            },
        ],
        "interaction_events": [
            {
                "trace_id": "interaction-1",
                "observed_at": "2026-04-05T09:11:00+08:00",
                "preference_signal": "prefers_direct_calorie_numbers",
                "action": "accepted",
            }
        ],
        "negative_preference_observations": [
            {
                "trace_id": "neg-1",
                "observed_at": "2026-04-05T12:15:00+08:00",
                "preference_scope": "ingredient",
                "value": "cilantro",
                "source_signal": "explicit_rejection",
                "confidence": 0.9,
            }
        ],
        "temporary_preference_observations": [
            {
                "trace_id": "temp-1",
                "observed_at": "2026-04-06T18:30:00+08:00",
                "preference_type": "temporary_constraint",
                "value": "lower_oil_dinner",
                "context_scope": "dinner",
                "valid_from": "2026-04-06",
                "valid_until": "2026-04-10",
                "confidence": 0.8,
            }
        ],
        "conversation_history_summaries": [
            {
                "trace_id": "conv-1",
                "conversation_id": "chat-2026-04-01",
                "observed_at": "2026-04-01T23:40:00+08:00",
                "summary": "User discussed late-night snack logging and wanted fewer repeated questions.",
                "topic_tags": ["late_logging", "followup_preference"],
            }
        ],
        "review_actions": [
            {
                "action_id": "review-accept-language",
                "target_candidate_ids": ["user-language-正常便當"],
                "action_type": "accept_candidate",
                "actor": "fixture_human_reviewer",
                "rationale": "Useful phrase for future intake clarification.",
            },
            {
                "action_id": "review-reject-usage",
                "target_candidate_ids": ["app-usage-style-pattern"],
                "action_type": "reject_candidate",
                "actor": "fixture_human_reviewer",
                "rationale": "Insufficient evidence for app usage style.",
            },
        ],
        "trace_metadata": [
            {"trace_id": "meal-1", "source_object_ref": "MealThread:m1"},
            {"trace_id": "budget-1", "source_object_ref": "DayBudgetLedger:2026-04-01"},
        ],
        "candidate_pool": [
            {
                "candidate_id": "food-1",
                "name": "oatmeal with latte",
                "source": "fixture",
                "estimated_kcal": 520,
                "tags": ["breakfast", "oats"],
            }
        ],
        "menu_scan_context": {
            "scan_source": "text_description",
            "restaurant_name": "Morning Bar",
            "parsed_items": [
                {
                    "item_name": "oatmeal with latte",
                    "estimated_kcal_range": [480, 560],
                    "confidence": 0.82,
                },
                {
                    "item_name": "cilantro chicken bowl",
                    "estimated_kcal_range": [620, 760],
                    "confidence": 0.71,
                },
            ],
            "parse_confidence": 0.78,
            "unparsed_items": [],
        },
    }


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
        "product_capability_context_map",
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


def test_memory_candidate_review_preserves_provenance_and_never_promotes_memory() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "long_term_memory_candidate_review"
    ]

    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["summary"]["candidate_count"] >= 4
    assert artifact["summary"]["golden_order_candidate_count"] == 1

    candidates = artifact["candidates"]
    oatmeal = next(
        candidate
        for candidate in candidates
        if candidate["candidate_type"] == "golden_order"
    )
    assert oatmeal["review_status"] == "pending"
    assert oatmeal["human_review_required"] is True
    assert oatmeal["runtime_effect_allowed"] is False
    assert oatmeal["source_trace_ids"] == ["meal-1", "meal-2", "meal-3"]
    assert oatmeal["source_object_refs"] == [
        "MealThread:m1",
        "MealThread:m2",
        "MealThread:m3",
    ]
    assert (
        oatmeal["proposed_memory_text"]
        == "Possible golden order: Morning Bar - oatmeal, latte"
    )
    assert oatmeal["scope_keys"] == {
        "user_id": "fixture-user",
        "workspace_id": "fixture_workspace",
        "project_id": "fixture_project",
        "surface": "fixture_shadow_lab",
    }
    assert oatmeal["secret_scan"]["status"] == "passed_no_secret_fields_detected"
    assert oatmeal["injection_eligibility"] == {
        "eligible": False,
        "reason": "shadow_lab_no_runtime_injection",
    }
    assert oatmeal["runtime_injection_allowed"] is False
    assert oatmeal["intended_consumers"] == [
        "recommendation",
        "intake_clarification",
        "chat_context",
    ]
    assert oatmeal["consumer_use_hints"]
    assert oatmeal["risk_if_wrong"]
    assert oatmeal["promotion_path"] == "human_review_then_l3_confirmed_memory_later"
    assert oatmeal["why_this_is_not_runtime_truth"]
    assert oatmeal["privacy_contract"] == {
        "raw_secret_values_stored": False,
        "scope_keys_required": True,
        "source_refs_required": True,
        "runtime_prompt_injection_allowed": False,
    }
    assert oatmeal["retention_posture"] == "shadow_review_artifact_only"

    for candidate in candidates:
        assert candidate["intended_consumers"]
        assert candidate["consumer_use_hints"]
        assert candidate["risk_if_wrong"]
        assert candidate["promotion_path"]
        assert candidate["why_this_is_not_runtime_truth"]
        assert candidate["runtime_effect_allowed"] is False
        assert candidate["runtime_injection_allowed"] is False


def test_memory_candidate_taxonomy_covers_language_bias_usage_and_interaction_domains() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "long_term_memory_candidate_review"
    ]
    by_type = {
        candidate["candidate_type"]: candidate for candidate in artifact["candidates"]
    }

    assert {
        "user_language_pattern",
        "intake_estimation_bias",
        "app_usage_style",
        "interaction_preference",
        "food_preference",
        "logging_adherence_pattern",
        "negative_preference",
        "temporary_preference",
        "conversation_recall_context",
    }.issubset(by_type)

    language = by_type["user_language_pattern"]
    assert language["payload"]["user_phrase"] == "正常便當"
    assert language["payload"]["pattern_subtype"] == "portion_phrase"
    assert language["payload"]["portion_semantics"] == {
        "portion_label": "normal_meal",
        "expected_components": ["rice", "main", "two_to_three_sides"],
    }
    assert language["intended_consumers"] == [
        "intake_clarification",
        "chat_context",
        "recommendation",
    ]

    bias = by_type["intake_estimation_bias"]
    assert bias["payload"]["bias_direction"] == "likely_underestimate"
    assert set(bias["payload"]["evidence_subtypes"]) == {
        "missed_item_pattern",
        "correction_tendency",
    }
    assert bias["payload"]["missed_item_patterns"] == ["drink_or_sauce"]
    assert bias["payload"]["correction_tendencies"] == ["adds_kcal_after_clarification"]
    assert bias["intended_consumers"] == [
        "calibration",
        "intake_risk_tagging",
        "nutrition_clarify_priority",
        "response_context",
    ]

    usage = by_type["app_usage_style"]
    assert usage["intended_consumers"] == [
        "chat_context",
        "proactive",
        "ux",
        "recommendation_presentation",
    ]

    interaction = by_type["interaction_preference"]
    assert interaction["intended_consumers"] == [
        "response_generation",
        "chat_context",
        "proactive_message_style",
    ]

    logging = by_type["logging_adherence_pattern"]
    assert "calibration" in logging["intended_consumers"]
    assert "rescue_later" in logging["intended_consumers"]

    negative = by_type["negative_preference"]
    assert negative["payload"]["value"] == "cilantro"
    assert negative["intended_consumers"] == [
        "recommendation",
        "proactive",
        "intake_clarification",
    ]

    temporary = by_type["temporary_preference"]
    assert temporary["payload"]["valid_until"] == "2026-04-10"
    assert temporary["intended_consumers"] == [
        "recommendation",
        "chat_context",
        "proactive",
        "intake_clarification",
    ]

    recall = by_type["conversation_recall_context"]
    assert recall["payload"]["summary_first"] is True
    assert recall["payload"]["raw_transcript_included"] is False
    assert recall["payload"]["manager_tool_call_allowed"] is False
    assert recall["intended_consumers"] == [
        "chat_context",
        "intake_clarification",
        "recommendation",
        "calibration",
    ]


def test_context_value_queue_explains_usefulness_and_early_injection_harm() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    queue = build_shadow_lab_artifacts(_fixture_payload())["context_value_review_queue"]

    assert queue["artifact_type"] == "context_value_review_queue"
    assert queue["items"]
    for item in queue["items"]:
        assert item["review_status"] == "pending"
        assert item["human_review_required"] is True
        assert item["runtime_effect_allowed"] is False
        assert item["possible_harm_if_injected_too_early"]
        assert item["recommended_next_action"] in {
            "keep_shadowing",
            "ask_user_to_confirm",
            "promote_to_confirmed_memory_later",
            "discard",
        }


def test_context_signal_quality_scorecard_prioritizes_value_and_harm_review() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "context_signal_quality_scorecard"
    ]

    assert artifact["artifact_type"] == "context_signal_quality_scorecard"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["scorecard_used_for_runtime_ranking"] is False

    by_id = {item["candidate_id"]: item for item in artifact["candidate_scores"]}
    assert (
        by_id["golden-order-morning-bar-oatmeal-latte"]["context_value_level"] == "high"
    )
    assert (
        by_id["intake-estimation-bias-likely-underestimate"]["harm_if_wrong_level"]
        == "high"
    )
    assert (
        by_id["intake-estimation-bias-likely-underestimate"][
            "recommended_review_action"
        ]
        == "keep_shadowing"
    )
    assert (
        by_id["negative-preference-ingredient-cilantro"]["recommended_review_action"]
        == "ask_user_to_confirm"
    )
    assert by_id["temporary-preference-lower-oil-dinner"]["expiry_sensitive"] is True

    rollups = {rollup["consumer_id"]: rollup for rollup in artifact["consumer_rollups"]}
    assert rollups["recommendation"]["candidate_count"] >= 4
    assert (
        "intake-estimation-bias-likely-underestimate"
        in rollups["calibration"]["candidate_ids"]
    )


def test_candidate_extraction_engine_v2_materializes_layers_profile_menu_and_highlights() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "candidate_extraction_engine_v2"
    ]

    assert artifact["artifact_type"] == "candidate_extraction_engine_v2"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["active_menu_scan_runtime_used"] is False

    assert artifact["memory_layers"] == [
        {
            "layer_id": "l1_typed_history_observation",
            "runtime_truth_owner": "canonical_typed_history",
            "durable_memory_written": False,
        },
        {
            "layer_id": "l2a_deterministic_pattern",
            "runtime_truth_owner": "shadow_deterministic_consolidation",
            "durable_memory_written": False,
        },
        {
            "layer_id": "l3_review_candidate_only",
            "runtime_truth_owner": "human_review_future_promotion",
            "durable_memory_written": False,
        },
    ]

    extracted = {
        candidate["candidate_id"]: candidate
        for candidate in artifact["extracted_candidates"]
    }
    language_candidate_id = next(
        candidate_id
        for candidate_id in extracted
        if candidate_id.startswith("user-language-")
    )
    assert "intake-estimation-bias-likely-underestimate" in extracted
    assert extracted[language_candidate_id]["payload_extracts"]["user_phrase"]
    assert extracted["intake-estimation-bias-likely-underestimate"]["payload_extracts"][
        "missed_item_patterns"
    ] == ["drink_or_sauce"]

    profile = artifact["shadow_profile_views"]["preference_profile_summary"]
    assert profile["is_durable_memory_truth"] is False
    assert profile["event_count"] == 4
    assert profile["top_stores"][0] == {"label": "Morning Bar", "count": 3}

    golden = artifact["shadow_profile_views"]["golden_order_summary"]
    assert golden["is_durable_memory_truth"] is False
    assert golden["orders"][0]["store_name"] == "Morning Bar"

    assert (
        artifact["menu_scan_shadow_context"]["runtime_recommendation_mode_started"]
        is False
    )
    assert artifact["menu_scan_shadow_context"]["restaurant_name"] == "Morning Bar"
    assert artifact["menu_scan_shadow_context"]["parsed_item_count"] == 2

    highlights = artifact["weekly_highlight_shadow_candidates"]
    assert highlights["derived_view_only"] is True
    assert "positive_highlights" in highlights
    assert highlights["narrative_summary_generated"] is False


def test_context_value_scoring_v2_scores_value_risk_recency_and_actions() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "context_value_scoring_v2"
    ]

    assert artifact["artifact_type"] == "context_value_scoring_v2"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["scorecard_used_for_runtime_ranking"] is False
    assert artifact["score_dimensions"] == [
        "evidence_strength_score",
        "recency_score",
        "frequency_score",
        "consumer_value_score",
        "harm_if_wrong_score",
        "contradiction_penalty",
        "review_priority_score",
    ]

    by_id = {item["candidate_id"]: item for item in artifact["candidate_scores"]}
    golden = by_id["golden-order-morning-bar-oatmeal-latte"]
    assert golden["review_priority_bucket"] == "high"
    assert golden["recommended_action"] == "ask_user_to_confirm"
    assert golden["product_capability_value"] == "direct_recommendation_or_intake_gain"

    bias = by_id["intake-estimation-bias-likely-underestimate"]
    assert bias["harm_if_wrong_level"] == "high"
    assert bias["recommended_action"] == "keep_shadowing"
    assert bias["product_capability_value"] == "calibration_or_clarification_gain"

    assert artifact["action_rollups"]["ask_user_to_confirm"] >= 1
    assert artifact["all_candidates_have_product_capability_value"] is True


def test_shadow_replay_evaluators_explain_used_and_ignored_context() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "shadow_replay_evaluators"
    ]

    assert artifact["artifact_type"] == "shadow_replay_evaluators"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["recommendation_served"] is False
    assert artifact["intake_commit_requested"] is False
    assert artifact["calibration_math_changed"] is False

    assert set(artifact["replays"]) == {
        "recommendation_shadow_replay",
        "intake_clarification_shadow_replay",
        "calibration_bias_shadow_replay",
        "conversation_recall_shadow_replay",
    }

    recommendation = artifact["replays"]["recommendation_shadow_replay"]
    assert recommendation["expected_user_value"] == "better_candidate_ranking_review"
    assert recommendation["menu_scan_context_used_as_candidate_source"] is True
    assert recommendation["runtime_recommendation_mode_started"] is False
    assert (
        "golden-order-morning-bar-oatmeal-latte" in recommendation["used_candidate_ids"]
    )
    assert recommendation["ignored_candidates"]

    intake = artifact["replays"]["intake_clarification_shadow_replay"]
    assert intake["expected_user_value"] == "fewer_but_better_followups_review"
    assert intake["clarification_policy"] in {
        "ask_targeted_followup",
        "use_phrase_pattern_with_caution",
    }
    assert any(
        candidate_id.startswith("user-language-")
        for candidate_id in intake["used_candidate_ids"]
    )

    calibration = artifact["replays"]["calibration_bias_shadow_replay"]
    assert calibration["expected_user_value"] == "better_bias_attribution_review"
    assert calibration["does_not_change_calibration_math"] is True
    assert (
        "intake-estimation-bias-likely-underestimate"
        in calibration["used_candidate_ids"]
    )

    conversation = artifact["replays"]["conversation_recall_shadow_replay"]
    assert conversation["expected_user_value"] == "better_cross_session_context_review"
    assert conversation["manager_tool_call_allowed"] is False
    assert conversation["raw_transcript_injected"] is False
    assert "conversation-recall-context-summary" in conversation["used_candidate_ids"]


def test_review_queue_reducer_prioritizes_product_value_without_artifact_sprawl() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())["review_queue_reducer"]

    assert artifact["artifact_type"] == "review_queue_reducer"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["artifact_sprawl_control"] == {
        "new_artifact_requires_declared_consumer": True,
        "new_artifact_requires_scoring_or_replay_use": True,
        "consumerless_candidates_deferred": True,
    }

    queue = artifact["review_queue"]
    assert set(queue) == {"high", "medium", "low", "rejected_or_deferred"}
    assert queue["high"]
    assert any(
        item["candidate_id"] == "negative-preference-ingredient-cilantro"
        for item in queue["high"]
    )
    assert all(
        item["runtime_effect_allowed"] is False
        for bucket in queue.values()
        for item in bucket
    )
    assert artifact["summary"]["candidate_count"] == sum(
        len(items) for items in queue.values()
    )
    assert artifact["summary"]["pseudo_runtime_truth_risk_count"] == 0

    reviews = {
        item["mechanism_id"]: item for item in artifact["deferred_mechanism_reviews"]
    }
    assert {
        "active_conversation_recall_tool",
        "durable_memory_write_service",
        "semantic_pattern_llm_extraction",
        "style_profile_materialization",
        "live_menu_scan_runtime",
    }.issubset(reviews)
    assert all(item["product_capability_value"] for item in reviews.values())
    assert all(item["blocked_by_dependency"] is True for item in reviews.values())


def test_context_pack_token_pressure_shadow_eval_preserves_l4c_ordering() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "context_pack_token_pressure_shadow_eval"
    ]

    assert artifact["artifact_type"] == "context_pack_token_pressure_shadow_eval"
    assert artifact["source_spec"] == "docs/specs/L4C_CONTEXT_PACKING_SPEC.md"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["token_pressure_policy"] == {
        "general_compaction_threshold": 0.6,
        "aggressive_compaction_threshold": 0.8,
        "forced_trim_threshold": 0.9,
    }
    assert artifact["prune_order"][:2] == [
        "long_transcript",
        "raw_historical_records",
    ]
    assert "current_task_object" in artifact["preserve_first"]
    assert "atomic_context_blocks" in artifact["preserve_first"]
    assert artifact["atomic_blocks_split_allowed"] is False
    assert {pack["pack_id"] for pack in artifact["evaluated_packs"]} >= {
        "recommendation",
        "intake_chat_context",
        "calibration_context",
        "proactive_context",
        "rescue_context",
        "cross_surface_context",
    }
    assert all(
        pack["raw_full_history_dumped"] is False for pack in artifact["evaluated_packs"]
    )


def test_product_capability_context_map_covers_whole_product_memory_consumers() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "product_capability_context_map"
    ]

    assert artifact["artifact_type"] == "product_capability_context_map"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["canonical_truth_replaced_by_memory"] is False
    assert {family["family_id"] for family in artifact["capability_families"]} == {
        "F1",
        "F2",
        "F3",
        "F4",
        "F5",
        "F6",
        "F7",
        "F8",
    }

    domain_ids = {domain["context_domain_id"] for domain in artifact["context_domains"]}
    assert {
        "food_preference_context",
        "negative_preference_context",
        "temporary_preference_context",
        "golden_order_context",
        "user_language_semantic_alias_context",
        "intake_estimation_bias_context",
        "app_usage_style_context",
        "interaction_preference_context",
        "logging_adherence_context",
        "conversation_recall_context",
        "proactive_suppression_context",
        "rescue_history_context",
        "calibration_quality_context",
        "cross_surface_context",
    }.issubset(domain_ids)

    by_family = {
        family["family_id"]: family for family in artifact["capability_families"]
    }
    assert "food_preference_context" in by_family["F6"]["context_domain_ids"]
    assert (
        "user_language_semantic_alias_context" in by_family["F2"]["context_domain_ids"]
    )
    assert "intake_estimation_bias_context" in by_family["F5"]["context_domain_ids"]
    assert "conversation_recall_context" in by_family["F8"]["context_domain_ids"]
    assert "proactive_suppression_context" in by_family["F7"]["context_domain_ids"]

    consumer_ids = {
        consumer["consumer_id"] for consumer in artifact["consumer_contracts"]
    }
    assert {
        "recommendation",
        "intake_clarification",
        "chat_context",
        "calibration",
        "proactive",
        "rescue_later",
        "cross_surface_experience",
    }.issubset(consumer_ids)

    assert (
        "negative_preference"
        not in artifact["coverage_gaps"]["fixture_missing_candidate_types"]
    )
    assert (
        "temporary_preference"
        not in artifact["coverage_gaps"]["fixture_missing_candidate_types"]
    )
    assert "docs/specs/L4A_MEMORY_MODEL_SPEC.md" in artifact["source_specs"]
    assert "docs/specs/L4C_CONTEXT_PACKING_SPEC.md" in artifact["source_specs"]


def test_review_actions_create_shadow_records_without_durable_memory_write() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "memory_review_action_shadow_result"
    ]

    assert artifact["artifact_type"] == "memory_review_action_shadow_result"
    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["summary"] == {
        "action_count": 2,
        "accepted_count": 1,
        "rejected_count": 1,
        "shadow_memory_record_count": 1,
        "missing_target_count": 0,
    }

    accepted = next(
        result
        for result in artifact["candidate_review_results"]
        if result["candidate_id"] == "user-language-正常便當"
    )
    assert accepted["review_status_after"] == "accepted"
    assert accepted["runtime_effect_allowed"] is False
    assert accepted["durable_memory_write_allowed"] is False

    record = artifact["shadow_memory_records"][0]
    assert record["source_candidate_id"] == "user-language-正常便當"
    assert record["record_state"] == "accepted_shadow"
    assert record["can_be_runtime_loaded"] is False
    assert record["durable_memory_written"] is False
    assert record["provenance"]["source_trace_ids"] == ["lang-1"]


def test_memory_promotion_demotion_shadow_eval_never_writes_durable_memory() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "memory_promotion_demotion_shadow_eval"
    ]

    assert artifact["artifact_type"] == "memory_promotion_demotion_shadow_eval"
    assert artifact["promotion_attempted"] is False
    assert artifact["demotion_attempted"] is False
    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["source_spec"] == "docs/specs/L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md"

    by_id = {item["candidate_id"]: item for item in artifact["promotion_review_items"]}
    language_item = next(
        item
        for item in artifact["promotion_review_items"]
        if item["candidate_id"].startswith("user-language-")
    )
    assert language_item["review_action_status"] == "accepted"
    assert language_item["durable_write_allowed"] is False
    assert by_id["negative-preference-ingredient-cilantro"]["promotion_blockers"] == [
        "human_confirmation_required"
    ]
    assert (
        by_id["temporary-preference-lower-oil-dinner"]["temporal_validity_required"]
        is True
    )
    assert by_id["temporary-preference-lower-oil-dinner"]["promotion_blockers"] == [
        "human_confirmation_required",
        "expiry_policy_required",
    ]

    demotion_lanes = {
        lane["lane_id"]: lane for lane in artifact["demotion_review_lanes"]
    }
    assert (
        demotion_lanes["expired_temporary_preference"]["automatic_runtime_effect"]
        is False
    )
    assert (
        demotion_lanes["user_correction_or_deletion"]["human_review_required"] is True
    )


def test_semantic_pattern_extraction_shadow_plan_keeps_llm_extraction_disabled() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "semantic_pattern_extraction_shadow_plan"
    ]

    assert artifact["artifact_type"] == "semantic_pattern_extraction_shadow_plan"
    assert artifact["source_spec"] == "docs/specs/L4A_MEMORY_MODEL_SPEC.md"
    assert artifact["llm_extraction_called"] is False
    assert artifact["semantic_memory_written"] is False
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["readiness_gate"] == {
        "required_new_committed_meal_items": 21,
        "required_days_since_last_extraction": 7,
        "fixture_committed_meal_items": 4,
        "extraction_allowed_now": False,
        "block_reason": "insufficient_committed_meal_items",
    }
    assert artifact["planned_output_schema"]["pattern_type_values"] == [
        "contextual_preference",
        "temporal_preference",
        "trend_shift",
        "situational_avoidance",
    ]
    assert artifact["intended_consumers"] == [
        "recommendation",
        "nightly_insight",
        "confirmed_memory_candidate_review",
    ]
    assert artifact["shadow_extraction_candidates"][0]["pattern_type"] == (
        "temporal_preference"
    )
    assert (
        artifact["shadow_extraction_candidates"][0]["durable_memory_write_allowed"]
        is False
    )


def test_conversation_recall_shadow_eval_is_summary_first_and_tool_call_disabled() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "conversation_recall_shadow_eval"
    ]

    assert artifact["artifact_type"] == "conversation_recall_shadow_eval"
    assert artifact["summary_first"] is True
    assert artifact["raw_transcript_included"] is False
    assert artifact["retrieval_tool_called"] is False
    assert artifact["manager_tool_call_allowed"] is False
    assert artifact["manager_context_injected"] is False
    assert (
        artifact["selected_context_candidates"][0]["candidate_type"]
        == "conversation_recall_context"
    )
    assert (
        artifact["selected_context_candidates"][0]["would_load_full_history"] is False
    )
    assert artifact["omission_trace"] == {
        "raw_transcript_omitted": True,
        "full_history_dump_omitted": True,
        "runtime_packet_injection_omitted": True,
    }


def test_conversation_recall_tool_shadow_plan_keeps_future_retrieval_disabled() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "conversation_recall_tool_shadow_plan"
    ]

    assert artifact["artifact_type"] == "conversation_recall_tool_shadow_plan"
    assert artifact["context_entry_mode"] == (
        "future_tool_mediated_retrieval_candidate"
    )
    assert artifact["manager_tool_registered"] is False
    assert artifact["manager_tool_called"] is False
    assert artifact["runtime_tool_available"] is False
    assert artifact["retrieval_tool_call_allowed_now"] is False
    assert artifact["raw_transcript_access_allowed_now"] is False
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["manager_context_injected"] is False

    contract = artifact["future_tool_contract"]
    assert contract["tool_name"] == "conversation_recall.search"
    assert contract["request_schema"]["required"] == [
        "user_id",
        "retrieval_query",
        "scope",
        "reason_for_recall",
    ]
    assert contract["response_contract"]["summary_first"] is True
    assert contract["response_contract"]["source_refs_required"] is True
    assert contract["response_contract"]["raw_transcript_returned"] is False
    assert contract["response_contract"]["manager_context_injection_allowed"] is False
    assert artifact["selected_conversation_refs"][0]["candidate_id"] == (
        "conversation-recall-context-summary"
    )
    assert (
        "ManagerContextPacket injection remains forbidden"
        in artifact["safety_boundaries"]
    )


def test_conversation_recall_retrieval_shadow_eval_routes_without_tool_calls() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "conversation_recall_retrieval_shadow_eval"
    ]

    assert artifact["artifact_type"] == "conversation_recall_retrieval_shadow_eval"
    assert artifact["retrieval_tool_registered"] is False
    assert artifact["retrieval_tool_called"] is False
    assert artifact["live_vector_search_used"] is False
    assert artifact["raw_transcript_returned"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["source_classes"] == [
        "conversation_history_summary",
        "memory_candidate_review_artifact",
    ]
    assert artifact["routing_policy"] == {
        "deterministic_scope_filter_first": True,
        "metadata_filter_before_semantic_search": True,
        "full_document_read_fallback_allowed": False,
        "stale_result_requires_review": True,
    }
    assert artifact["ranked_results"][0]["candidate_id"] == (
        "conversation-recall-context-summary"
    )
    assert artifact["negative_cases"][0] == {
        "case_id": "missing_user_scope",
        "retrieval_allowed": False,
        "reason": "scope_keys_required_before_recall",
    }


def test_entity_normalization_shadow_plan_stays_review_only() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "entity_normalization_shadow_plan"
    ]

    assert artifact["artifact_type"] == "entity_normalization_shadow_plan"
    assert artifact["entity_store_written"] is False
    assert artifact["fooddb_truth_changed"] is False
    assert artifact["canonical_objects_replaced"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["entity_types"] == [
        "food_item",
        "store",
        "user_phrase",
        "preference_value",
        "conversation_topic",
    ]
    proposed_ids = {entity["entity_id"] for entity in artifact["proposed_entities"]}
    assert "store-morning-bar" in proposed_ids
    assert "food-oatmeal" in proposed_ids
    assert "preference-value-cilantro" in proposed_ids
    assert artifact["normalization_review_lanes"][0]["runtime_effect_allowed"] is False


def test_context_quality_contradiction_review_flags_shadow_conflicts() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    fixture = _fixture_payload()
    fixture["candidate_pool"].append(
        {"candidate_id": "food-cilantro", "name": "cilantro chicken bowl"}
    )

    artifact = build_shadow_lab_artifacts(fixture)[
        "context_quality_contradiction_review_queue"
    ]

    assert artifact["artifact_type"] == "context_quality_contradiction_review_queue"
    assert artifact["runtime_blocking_claimed"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["contradiction_count"] >= 1
    conflict = next(
        item
        for item in artifact["review_items"]
        if item["check_id"] == "negative_preference_vs_candidate_pool"
    )
    assert conflict["review_status"] == "pending"
    assert conflict["runtime_effect_allowed"] is False
    assert conflict["recommended_action"] == "keep_shadowing"
    assert "negative-preference-ingredient-cilantro" in conflict["candidate_ids"]


def test_capability_scenario_fixture_pack_covers_consumer_paths_without_runtime() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "capability_scenario_fixture_pack"
    ]

    assert artifact["artifact_type"] == "capability_scenario_fixture_pack"
    assert artifact["runtime_scenarios_executed"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["fixture_only"] is True
    assert {scenario["consumer_id"] for scenario in artifact["scenarios"]} == {
        "recommendation",
        "intake_clarification",
        "chat_context",
        "calibration",
        "proactive",
        "rescue_later",
        "conversation_recall",
    }
    for scenario in artifact["scenarios"]:
        assert scenario["runtime_effect_allowed"] is False
        assert scenario["expected_artifact_ids"]
        assert scenario["forbidden_runtime_effects"]


def test_pr_review_autopilot_closeout_is_draft_pr_only() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "pr_review_autopilot_closeout"
    ]

    assert artifact["artifact_type"] == "pr_review_autopilot_closeout"
    assert artifact["draft_pr_only"] is True
    assert artifact["auto_merge_allowed"] is False
    assert artifact["human_approval_required_for_merge"] is True
    assert artifact["continue_without_gate_after_batch2"] is False
    assert artifact["runtime_effect_allowed"] is False


def test_consumer_specific_context_packs_are_summary_first_and_non_injecting() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "long_term_context_pack_shadow_eval"
    ]

    assert artifact["artifact_type"] == "long_term_context_pack_shadow_eval"
    assert artifact["manager_context_injected"] is False
    assert artifact["runtime_context_loaded"] is False
    assert set(artifact["context_packs"]) == {
        "recommendation",
        "intake_chat_context",
        "calibration_context",
        "proactive_context",
        "rescue_context",
        "cross_surface_context",
    }

    for pack in artifact["context_packs"].values():
        assert pack["summary_first"] is True
        assert pack["structured_state_first"] is True
        assert pack["raw_full_history_dumped"] is False
        assert pack["runtime_effect_allowed"] is False
        assert pack["manager_context_injection_allowed"] is False
        assert pack["token_estimate"] >= 0
        assert pack["omission_trace"]["raw_transcript_omitted"] is True
        assert pack["omission_trace"]["unselected_candidates_omitted"] >= 0

    recommendation = artifact["context_packs"]["recommendation"]
    assert (
        "golden-order-morning-bar-oatmeal-latte"
        in recommendation["selected_candidate_ids"]
    )
    assert "preference-drink-latte" in recommendation["selected_candidate_ids"]
    assert (
        "negative-preference-ingredient-cilantro"
        in recommendation["selected_candidate_ids"]
    )
    assert (
        "temporary-preference-lower-oil-dinner"
        in recommendation["selected_candidate_ids"]
    )

    intake_chat = artifact["context_packs"]["intake_chat_context"]
    assert any(
        candidate_id.startswith("user-language-")
        for candidate_id in intake_chat["selected_candidate_ids"]
    )
    assert (
        "conversation-recall-context-summary" in intake_chat["selected_candidate_ids"]
    )

    calibration = artifact["context_packs"]["calibration_context"]
    assert (
        "intake-estimation-bias-likely-underestimate"
        in calibration["selected_candidate_ids"]
    )
    assert "pattern-budget-overshoot-frequency" in calibration["selected_candidate_ids"]

    proactive = artifact["context_packs"]["proactive_context"]
    assert "app-usage-style-pattern" in proactive["selected_candidate_ids"]
    assert (
        "interaction-preference-prefers-direct-calorie-numbers"
        in proactive["selected_candidate_ids"]
    )

    rescue = artifact["context_packs"]["rescue_context"]
    assert "pattern-budget-overshoot-frequency" in rescue["selected_candidate_ids"]
    assert "pattern-weight-logging-consistency" in rescue["selected_candidate_ids"]

    cross_surface = artifact["context_packs"]["cross_surface_context"]
    assert "app-usage-style-pattern" in cross_surface["selected_candidate_ids"]
    assert (
        "conversation-recall-context-summary" in cross_surface["selected_candidate_ids"]
    )


def test_shadow_simulations_never_send_serve_or_commit() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifacts = build_shadow_lab_artifacts(_fixture_payload())

    proactive = artifacts["proactive_no_send_simulation"]
    assert proactive["proactive_sent"] is False
    assert proactive["scheduler_activated"] is False
    assert proactive["would_inject_context"] is False
    assert proactive["injection_position"] == "not_applicable_shadow"
    assert proactive["token_estimate"] >= 0
    assert proactive["candidate_triggers"]

    recommendation = artifacts["recommendation_shadow_eval"]
    assert recommendation["recommendation_served"] is False
    assert recommendation["live_search_used"] is False
    assert recommendation["candidate_evaluations"]
    used_context_ids = recommendation["candidate_evaluations"][0][
        "used_context_candidate_ids"
    ]
    assert "preference-drink-latte" in used_context_ids

    rescue = artifacts["rescue_shadow_candidates"]
    assert rescue["rescue_committed"] is False
    assert rescue["budget_mutation_requested"] is False
    assert rescue["candidate_packets"]

    trigger_ids = {trigger["trigger_id"] for trigger in proactive["candidate_triggers"]}
    assert "trigger-preference-drink-latte" in trigger_ids


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
        "product_capability_context_map.json",
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
