from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from app.advanced_shadow_lab.product_lab_proactive_control_store import (
    ProductLabProactiveControlStore,
)
from app.shared.infra.json_artifacts import read_json_artifact
from tests.test_advanced_product_lab_runtime import _fixture_inputs


def test_session_replay_bridges_chat_dismiss_to_control_journal(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="lab-session-chat-dismiss-control",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-dismiss",
                "lab_now_minute": 10,
                "post_turn_chat_actions": [
                    {
                        "event_id": "dismiss-rec-chat",
                        "target_candidate_id": "recommendation_prompt:0",
                        "action": "dismiss",
                        "dismiss_reason": "too_frequent",
                    }
                ],
            },
            {"turn_id": "t2-after-dismiss", "lab_now_minute": 20},
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["control_event_history_ids"] == ["dismiss-rec-chat"]
    assert artifact["final_control_journal_event_ids"] == ["dismiss-rec-chat"]
    assert artifact["proactive_control_store_lab_isolated"] is True
    assert artifact["proactive_control_store_path"]
    assert ProductLabProactiveControlStore(tmp_path).read_journal(
        session_id="lab-session-chat-dismiss-control"
    ) == artifact["final_control_journal_entries"]
    assert _visible_by_turn(artifact) == {
        "t1-dismiss": ["recommendation_prompt:0", "rescue_nudge:1"],
        "t2-after-dismiss": ["rescue_nudge:1"],
    }

    first_turn = read_json_artifact(Path(artifact["turn_artifact_paths"][0]))
    [entry] = first_turn["post_turn_control_state"]["journal_entries"]
    assert entry["trigger_type"] == "recommendation_prompt"
    assert entry["next_signal_required"] == "new_app_open_with_qualified_pool"
    assert entry["source_packet_id"] == "recommendation_prompt:0"
    assert entry["source_workflow_family"] == "recommendation"
    assert entry["raw_user_text_semantic_inference_performed"] is False
    assert entry["canonical_product_mutation_allowed"] is False


def test_session_replay_bridges_chat_snooze_and_releases_after_window(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="lab-session-chat-snooze-control",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-snooze",
                "lab_now_minute": 10,
                "post_turn_chat_actions": [
                    {
                        "event_id": "snooze-rescue-chat",
                        "target_candidate_id": "rescue_nudge:1",
                        "action": "snooze",
                        "snooze_minutes": 60,
                    }
                ],
            },
            {"turn_id": "t2-before-release", "lab_now_minute": 30},
            {"turn_id": "t3-after-release", "lab_now_minute": 71},
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["control_event_history_ids"] == ["snooze-rescue-chat"]
    assert artifact["final_control_journal_event_ids"] == []
    assert _visible_by_turn(artifact) == {
        "t1-snooze": ["recommendation_prompt:0", "rescue_nudge:1"],
        "t2-before-release": ["recommendation_prompt:0"],
        "t3-after-release": ["recommendation_prompt:0", "rescue_nudge:1"],
    }

    second_turn = read_json_artifact(Path(artifact["turn_artifact_paths"][1]))
    rescue_state = _candidate_state(second_turn, "rescue_nudge:1")
    assert rescue_state["visible_in_lab"] is False
    assert rescue_state["suppression_reason"] == "snoozed_until_release"


def test_session_replay_bridges_chat_undo_without_hidden_target_action(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="lab-session-chat-undo-control",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-dismiss-then-undo",
                "lab_now_minute": 10,
                "post_turn_chat_actions": [
                    {
                        "event_id": "dismiss-rec-chat",
                        "target_candidate_id": "recommendation_prompt:0",
                        "action": "dismiss",
                        "dismiss_reason": "too_frequent",
                    },
                    {
                        "event_id": "undo-rec-chat",
                        "target_candidate_id": "recommendation_prompt:0",
                        "action": "undo",
                        "undo_event_id": "dismiss-rec-chat",
                    },
                ],
            },
            {"turn_id": "t2-after-undo", "lab_now_minute": 20},
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["control_event_history_ids"] == [
        "dismiss-rec-chat",
        "undo-rec-chat",
    ]
    assert _visible_by_turn(artifact) == {
        "t1-dismiss-then-undo": ["recommendation_prompt:0", "rescue_nudge:1"],
        "t2-after-undo": ["recommendation_prompt:0", "rescue_nudge:1"],
    }

    second_turn = read_json_artifact(Path(artifact["turn_artifact_paths"][1]))
    restored = _candidate_state(second_turn, "recommendation_prompt:0")
    assert restored["visible_in_lab"] is True
    assert restored["suppression_reason"] == "restored_by_undo"
    assert restored["active_control_event_id"] == "undo-rec-chat"


def _visible_by_turn(artifact: dict[str, object]) -> dict[str, list[str]]:
    return {
        row["turn_id"]: row["visible_candidate_ids"]
        for row in artifact["turn_summaries"]  # type: ignore[index]
    }


def _candidate_state(turn_record: dict[str, object], candidate_id: str) -> dict[str, object]:
    states = turn_record["turn_artifact"]["lab_chat_response_packet"]["candidate_states"]  # type: ignore[index]
    for state in states:
        if state["candidate_id"] == candidate_id:
            return state
    raise AssertionError(f"candidate state not found: {candidate_id}")
