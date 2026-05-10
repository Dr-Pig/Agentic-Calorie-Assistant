from __future__ import annotations

import json
from pathlib import Path

from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from app.shared.infra.json_artifacts import read_json_artifact
from tests.test_advanced_product_lab_runtime import _fixture_inputs


def test_product_lab_session_replay_persists_controls_across_turns(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="lab-session-replay-1",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-offer",
                "lab_now_minute": 10,
                "post_turn_control_events": [
                    {
                        "event_id": "dismiss-rec",
                        "action": "dismiss",
                        "target_candidate_id": "recommendation_prompt:0",
                        "trigger_type": "recommendation_prompt",
                        "scope": "candidate_instance",
                        "dismiss_reason": "too_frequent",
                        "next_signal_required": "new_app_open_with_qualified_pool",
                    }
                ],
            },
            {"turn_id": "t2-after-dismiss", "lab_now_minute": 20},
            {
                "turn_id": "t3-material-signal",
                "lab_now_minute": 30,
                "observed_material_signals": ["new_app_open_with_qualified_pool"],
                "post_turn_control_events": [
                    {
                        "event_id": "snooze-rescue",
                        "action": "snooze",
                        "target_candidate_id": "rescue_nudge:1",
                        "trigger_type": "rescue_nudge",
                        "scope": "candidate_instance",
                        "snooze_minutes": 60,
                        "release_signal": (
                            "material_budget_change_or_user_reopens_rescue"
                        ),
                    }
                ],
            },
            {"turn_id": "t4-before-snooze-release", "lab_now_minute": 70},
        ],
    )

    assert artifact["artifact_type"] == "advanced_product_lab_dogfood_session_artifact"
    assert artifact["status"] == "pass"
    assert artifact["session_id"] == "lab-session-replay-1"
    assert artifact["turn_count"] == 4
    assert artifact["lab_session_store_written"] is True
    assert artifact["lab_user_facing_behavior_changed"] is True
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["mainline_runtime_connected"] is False
    assert artifact["production_scheduler_delivery_allowed"] is False
    assert artifact["production_db_migration_allowed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["manager_context_packet_changed"] is False

    visible_by_turn = {
        row["turn_id"]: row["visible_candidate_ids"]
        for row in artifact["turn_summaries"]
    }
    assert visible_by_turn == {
        "t1-offer": ["recommendation_prompt:0", "rescue_nudge:1"],
        "t2-after-dismiss": ["rescue_nudge:1"],
        "t3-material-signal": ["recommendation_prompt:0", "rescue_nudge:1"],
        "t4-before-snooze-release": ["recommendation_prompt:0"],
    }
    assert artifact["control_event_history_ids"] == [
        "dismiss-rec",
        "snooze-rescue",
    ]
    assert artifact["final_control_journal_event_ids"] == ["snooze-rescue"]

    session_path = Path(artifact["session_artifact_path"])
    assert session_path.exists()
    persisted_session = read_json_artifact(session_path)
    assert persisted_session["turn_count"] == 4
    assert persisted_session["control_event_history_ids"] == [
        "dismiss-rec",
        "snooze-rescue",
    ]
    assert persisted_session["final_control_journal_event_ids"] == ["snooze-rescue"]

    turn_paths = [Path(path) for path in artifact["turn_artifact_paths"]]
    assert len(turn_paths) == 4
    assert all(path.exists() for path in turn_paths)
    t2 = read_json_artifact(turn_paths[1])
    assert [
        message["candidate_id"]
        for message in t2["turn_artifact"]["lab_chat_surface"]["messages"]
    ] == ["rescue_nudge:1"]
    serialized = json.dumps(artifact, ensure_ascii=False)
    assert session_path.is_relative_to(tmp_path.resolve(strict=False))
    assert "production_db_path" not in serialized.lower()


def test_product_lab_session_replay_records_post_turn_chat_action_outcomes(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="lab-session-actions-1",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-action",
                "post_turn_chat_actions": [
                    {
                        "event_id": "log-recommendation",
                        "target_candidate_id": "recommendation_prompt:0",
                        "action": "log_this",
                    },
                    {
                        "event_id": "accept-rescue",
                        "target_candidate_id": "rescue_nudge:1",
                        "action": "accept_rescue_plan",
                    },
                ],
            }
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_chat_action_outcome_count"] == 2
    assert artifact["lab_chat_action_outcome_types"] == [
        "recommendation_intake_draft",
        "rescue_commit_confirmation",
    ]
    assert artifact["lab_chat_action_canonical_mutation_allowed"] is False
    assert artifact["lab_chat_action_blockers"] == []
    assert artifact["lab_pending_intake_draft_count"] == 1
    assert artifact["lab_pending_intake_draft_candidate_ids"] == ["golden-1"]
    assert artifact["lab_pending_intake_draft_canonical_mutation_allowed"] is False
    assert "memory_candidate:golden-1" in artifact[
        "lab_pending_intake_draft_source_refs"
    ]
    assert artifact["lab_rescue_action_decision_count"] == 1
    assert artifact["lab_rescue_action_decision_kinds"] == [
        "pending_rescue_commit_confirmation"
    ]
    assert artifact["lab_rescue_commit_pending_count"] == 1
    assert artifact["lab_rescue_action_canonical_mutation_allowed"] is False
    assert "rescue_proposal_card:same_day_rescue_lab" in artifact[
        "lab_rescue_action_decision_source_refs"
    ]
    action_state = artifact["lab_action_state"]
    assert action_state["active_pending_intake_draft_ids"] == ["golden-1"]
    assert action_state["rescue_commit_pending_count"] == 1
    assert action_state["dismissed_rescue_instance_count"] == 0
    assert action_state["requested_rescue_next_signals"] == []
    assert action_state["canonical_product_mutation_allowed"] is False
    assert artifact["canonical_product_mutation_allowed"] is False

    [turn_summary] = artifact["turn_summaries"]
    assert turn_summary["lab_chat_action_outcome_count"] == 2
    assert turn_summary["lab_chat_action_event_ids"] == [
        "log-recommendation",
        "accept-rescue",
    ]
    assert turn_summary["lab_chat_action_outcome_types"] == [
        "recommendation_intake_draft",
        "rescue_commit_confirmation",
    ]
    assert turn_summary["lab_pending_intake_draft_count"] == 1
    assert turn_summary["lab_pending_intake_draft_candidate_ids"] == ["golden-1"]
    assert turn_summary["lab_rescue_action_decision_count"] == 1
    assert turn_summary["lab_rescue_commit_pending_count"] == 1

    [turn_path] = [Path(path) for path in artifact["turn_artifact_paths"]]
    turn_record = read_json_artifact(turn_path)
    outcomes = turn_record["post_turn_chat_action_outcomes"]
    assert [item["target_candidate_id"] for item in outcomes] == [
        "recommendation_prompt:0",
        "rescue_nudge:1",
    ]
    draft = outcomes[0]["pending_intake_draft_packet"]
    assert draft["status"] == "pass"
    assert draft["requires_followup_commit_confirmation"] is True
    assert draft["actual_intake_observed"] is False
    assert draft["canonical_product_mutation_allowed"] is False
    rescue_decision = outcomes[1]["rescue_action_decision_packet"]
    assert rescue_decision["status"] == "pass"
    assert rescue_decision["decision_kind"] == "pending_rescue_commit_confirmation"
    assert rescue_decision["lab_rescue_commit_pending"] is True
    assert rescue_decision["proposal_committed"] is False
    assert rescue_decision["ledger_entry_created"] is False
    state_delta = turn_record["post_turn_action_state_delta"]
    assert state_delta["pending_intake_draft_ids_added"] == ["golden-1"]
    assert state_delta["rescue_commit_pending_added"] == 1
    assert state_delta["dismissed_rescue_instance_added"] == 0
    assert turn_record["post_turn_action_state"]["rescue_commit_pending_count"] == 1
    assert all(
        item["canonical_product_mutation_allowed"] is False for item in outcomes
    )


def test_product_lab_session_replay_distinguishes_rescue_non_commit_actions(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="lab-session-rescue-actions-1",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-action",
                "post_turn_chat_actions": [
                    {
                        "event_id": "dismiss-rescue",
                        "target_candidate_id": "rescue_nudge:1",
                        "action": "dismiss_rescue_plan",
                    },
                    {
                        "event_id": "gentler-rescue",
                        "target_candidate_id": "rescue_nudge:1",
                        "action": "request_gentler_plan",
                    },
                    {
                        "event_id": "why-rescue",
                        "target_candidate_id": "rescue_nudge:1",
                        "action": "ask_why_this_plan",
                    },
                ],
            }
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_rescue_action_decision_count"] == 3
    assert artifact["lab_rescue_action_decision_kinds"] == [
        "dismiss_current_proposal_instance",
        "request_gentler_variant",
        "request_explanation",
    ]
    assert artifact["lab_rescue_commit_pending_count"] == 0
    assert artifact["lab_action_state"]["dismissed_rescue_instance_count"] == 1
    assert artifact["lab_action_state"]["rescue_commit_pending_count"] == 0
    assert artifact["lab_action_state"]["requested_rescue_next_signals"] == [
        "material_context_change_or_user_reopens_rescue",
        "chat_negotiation_requested_gentler_plan",
        "chat_explanation_requested",
    ]
    assert artifact["lab_rescue_action_canonical_mutation_allowed"] is False
    assert artifact["canonical_product_mutation_allowed"] is False

    [turn_path] = [Path(path) for path in artifact["turn_artifact_paths"]]
    outcomes = read_json_artifact(turn_path)["post_turn_chat_action_outcomes"]
    assert [item["rescue_action_decision_packet"]["requested_next_signal"] for item in outcomes] == [
        "material_context_change_or_user_reopens_rescue",
        "chat_negotiation_requested_gentler_plan",
        "chat_explanation_requested",
    ]
    assert all(
        item["rescue_action_decision_packet"]["lab_rescue_commit_pending"] is False
        for item in outcomes
    )


def test_product_lab_session_replay_action_state_is_cross_turn_projection(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="lab-session-action-state-1",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-log",
                "post_turn_chat_actions": [
                    {
                        "event_id": "log-recommendation",
                        "target_candidate_id": "recommendation_prompt:0",
                        "action": "log_this",
                    }
                ],
            },
            {
                "turn_id": "t2-accept-rescue",
                "post_turn_chat_actions": [
                    {
                        "event_id": "accept-rescue",
                        "target_candidate_id": "rescue_nudge:1",
                        "action": "accept_rescue_plan",
                    }
                ],
            },
        ],
    )

    assert artifact["status"] == "pass"
    state = artifact["lab_action_state"]
    assert state["artifact_type"] == "advanced_product_lab_action_state"
    assert state["active_pending_intake_draft_ids"] == ["golden-1"]
    assert state["rescue_commit_pending_count"] == 1
    assert state["canonical_product_mutation_allowed"] is False
    assert state["durable_product_memory_written"] is False
    assert artifact["canonical_product_mutation_allowed"] is False

    turn_paths = [Path(path) for path in artifact["turn_artifact_paths"]]
    first = read_json_artifact(turn_paths[0])
    second = read_json_artifact(turn_paths[1])
    assert first["post_turn_action_state_delta"][
        "pending_intake_draft_ids_added"
    ] == ["golden-1"]
    assert first["post_turn_action_state"]["rescue_commit_pending_count"] == 0
    assert second["post_turn_action_state_delta"]["rescue_commit_pending_added"] == 1
    assert second["post_turn_action_state"]["active_pending_intake_draft_ids"] == [
        "golden-1"
    ]


def test_product_lab_session_replay_records_manager_tool_loop_trace(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="lab-session-manager-loop-1",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-memory-write",
                "post_turn_memory_events": [
                    {
                        "memory_id": "golden-bento-1",
                        "memory_type": "golden_order",
                        "summary": "Often chooses a FamilyMart chicken bento for lunch.",
                        "review_status": "accepted_lab",
                        "source_object_refs": ["meal_thread:seed-1"],
                        "intended_consumers": ["recommendation", "proactive"],
                        "store_name": "FamilyMart",
                        "item_names": ["chicken bento"],
                        "estimated_kcal": 520,
                    }
                ],
            },
            {
                "turn_id": "t2-manager-loop",
                "manager_script": _manager_script(),
            },
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["manager_tool_loop_turn_count"] == 1
    assert artifact["manager_tool_loop_source_refs"] == [
        "manager_tool_call:memory-search-1:memory.search",
        "manager_tool_call:recommendation-1:recommendation.run",
        "manager_tool_call:rescue-1:rescue.run",
        "manager_tool_call:proactive-1:proactive.run",
    ]
    assert artifact["manager_tool_loop_blockers"] == []
    assert artifact["turn_summaries"][0]["manager_tool_loop_status"] == "not_run"
    assert artifact["turn_summaries"][1]["manager_tool_loop_status"] == "pass"
    assert artifact["turn_summaries"][1]["manager_tool_loop_enabled"] is True
    assert artifact["turn_summaries"][1]["manager_tool_loop_source_refs"] == (
        artifact["manager_tool_loop_source_refs"]
    )

    turn_path = Path(artifact["turn_artifact_paths"][1])
    turn_record = read_json_artifact(turn_path)
    manager_artifact = turn_record["turn_artifact"]["manager_tool_loop_artifact"]
    memory_result = manager_artifact["tool_result_trace"][0]["result_artifact"]
    assert memory_result["context_pack"]["selected_record_ids"] == ["golden-bento-1"]
    assert turn_record["turn_artifact"]["user_facing_behavior_changed"] is False
    assert turn_record["turn_artifact"]["canonical_product_mutation_allowed"] is False


def test_product_lab_session_replay_blocks_invisible_chat_action_target(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="lab-session-action-edge-1",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-dismiss",
                "lab_now_minute": 10,
                "post_turn_control_events": [
                    {
                        "event_id": "dismiss-rec",
                        "action": "dismiss",
                        "target_candidate_id": "recommendation_prompt:0",
                        "trigger_type": "recommendation_prompt",
                        "scope": "candidate_instance",
                        "dismiss_reason": "too_frequent",
                        "next_signal_required": "new_app_open_with_qualified_pool",
                    }
                ],
            },
            {
                "turn_id": "t2-invalid-action",
                "lab_now_minute": 20,
                "post_turn_chat_actions": [
                    {
                        "event_id": "log-invisible-rec",
                        "target_candidate_id": "recommendation_prompt:0",
                        "action": "log_this",
                    }
                ],
            },
        ],
    )

    assert artifact["status"] == "blocked"
    assert artifact["lab_session_store_written"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["lab_chat_action_blockers"] == [
        "chat_action.target_not_visible:recommendation_prompt:0"
    ]
    assert artifact["lab_pending_intake_draft_count"] == 0
    assert artifact["lab_pending_intake_draft_source_refs"] == []
    assert artifact["lab_rescue_action_decision_count"] == 0
    assert artifact["lab_action_state"]["active_pending_intake_draft_ids"] == []
    assert artifact["lab_action_state"]["rescue_commit_pending_count"] == 0
    assert artifact["blockers"] == [
        "t2-invalid-action.chat_action.chat_action.target_not_visible:recommendation_prompt:0"
    ]
    assert artifact["turn_summaries"][1]["visible_candidate_ids"] == [
        "rescue_nudge:1"
    ]
    assert artifact["turn_summaries"][1]["lab_chat_action_outcome_types"] == [
        "target_candidate_not_visible"
    ]


def test_product_lab_session_replay_blocks_path_traversal_session_id(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="../escape",
        fixture_inputs=_fixture_inputs(),
        turns=[{"turn_id": "t1-offer"}],
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["session_id.unsafe_path_segment"]
    assert artifact["lab_session_store_written"] is False
    assert artifact["user_facing_behavior_changed"] is False


def _manager_script() -> list[dict[str, object]]:
    return [
        {
            "pass_id": "manager-pass-1",
            "action": "call_tools",
            "tool_calls": [
                {
                    "call_id": "memory-search-1",
                    "tool_name": "memory.search",
                    "arguments": {
                        "consumers": ["recommendation", "proactive"],
                        "token_budget": 200,
                    },
                }
            ],
        },
        {
            "pass_id": "manager-pass-2",
            "action": "call_tools",
            "tool_calls": [
                {
                    "call_id": "recommendation-1",
                    "tool_name": "recommendation.run",
                    "arguments": {"memory_context_call_id": "memory-search-1"},
                },
                {
                    "call_id": "rescue-1",
                    "tool_name": "rescue.run",
                    "arguments": {},
                },
            ],
        },
        {
            "pass_id": "manager-pass-3",
            "action": "call_tools",
            "tool_calls": [
                {
                    "call_id": "proactive-1",
                    "tool_name": "proactive.run",
                    "arguments": {
                        "memory_context_call_id": "memory-search-1",
                        "recommendation_call_id": "recommendation-1",
                        "rescue_call_id": "rescue-1",
                    },
                }
            ],
        },
        {
            "pass_id": "manager-pass-4",
            "action": "final",
            "final_response": {
                "copy": "Fixture manager synthesis from returned tool results.",
                "source_tool_call_ids": [
                    "memory-search-1",
                    "recommendation-1",
                    "rescue-1",
                    "proactive-1",
                ],
            },
        },
    ]
