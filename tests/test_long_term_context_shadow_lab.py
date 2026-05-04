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
                "confidence": 0.62,
            }
        ],
        "intake_estimation_events": [
            {
                "trace_id": "bias-1",
                "observed_at": "2026-04-03T22:15:00+08:00",
                "bias_direction": "likely_underestimate",
                "reason": "missed_drink_or_sauce",
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
            }
        ],
    }


def test_shadow_lab_builds_review_artifacts_with_required_non_claim_flags() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        SHADOW_NON_CLAIM_FLAGS,
        build_shadow_lab_artifacts,
    )

    artifacts = build_shadow_lab_artifacts(_fixture_payload())

    assert set(artifacts) == {
        "long_term_memory_candidate_review",
        "context_value_review_queue",
        "proactive_no_send_simulation",
        "recommendation_shadow_eval",
        "rescue_shadow_candidates",
        "memory_review_action_shadow_result",
        "conversation_recall_shadow_eval",
        "long_term_context_pack_shadow_eval",
        "conversation_recall_tool_shadow_plan",
    }

    for artifact in artifacts.values():
        for key, expected in SHADOW_NON_CLAIM_FLAGS.items():
            assert artifact[key] is expected
        assert artifact["fixture_input_used"] is True
        assert artifact["real_dogfood_export_used"] is False


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
        "conversation_recall_context",
    }.issubset(by_type)

    language = by_type["user_language_pattern"]
    assert language["payload"]["user_phrase"] == "正常便當"
    assert language["intended_consumers"] == [
        "intake_clarification",
        "chat_context",
        "recommendation",
    ]

    bias = by_type["intake_estimation_bias"]
    assert bias["payload"]["bias_direction"] == "likely_underestimate"
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
        "long_term_memory_candidate_review.json",
        "context_value_review_queue.json",
        "proactive_no_send_simulation.json",
        "recommendation_shadow_eval.json",
        "rescue_shadow_candidates.json",
        "memory_review_action_shadow_result.json",
        "conversation_recall_shadow_eval.json",
        "long_term_context_pack_shadow_eval.json",
        "conversation_recall_tool_shadow_plan.json",
        "external_memory_framework_research_review.json",
    }
    assert {path.name for path in output_dir.iterdir()} == expected_files
    for path in output_dir.iterdir():
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["shadow_mode"] is True
        assert payload["real_runtime_effect"] is False
