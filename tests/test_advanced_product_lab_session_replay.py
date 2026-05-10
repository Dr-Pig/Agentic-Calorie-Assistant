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

    [turn_path] = [Path(path) for path in artifact["turn_artifact_paths"]]
    turn_record = read_json_artifact(turn_path)
    outcomes = turn_record["post_turn_chat_action_outcomes"]
    assert [item["target_candidate_id"] for item in outcomes] == [
        "recommendation_prompt:0",
        "rescue_nudge:1",
    ]
    assert all(
        item["canonical_product_mutation_allowed"] is False for item in outcomes
    )


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
