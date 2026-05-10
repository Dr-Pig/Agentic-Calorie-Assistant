from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from app.shared.infra.json_artifacts import read_json_artifact
from tests.test_advanced_product_lab_runtime import _fixture_inputs


def test_pending_intake_followup_confirm_closes_lab_draft(
    tmp_path: Path,
) -> None:
    artifact = _session_with_pending_action(tmp_path, "confirm_pending_intake")

    assert artifact["status"] == "pass"
    assert artifact["lab_pending_intake_terminal_count"] == 1
    assert artifact["lab_pending_intake_terminal_states"] == [
        "confirmed_lab_intake"
    ]
    assert artifact["lab_action_state"]["active_pending_intake_draft_ids"] == []
    assert artifact["lab_action_state"]["active_pending_intake_source_refs"] == []
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["durable_product_memory_written"] is False

    second_turn = read_json_artifact(Path(artifact["turn_artifact_paths"][1]))
    [outcome] = second_turn["post_turn_chat_action_outcomes"]
    packet = outcome["pending_intake_lifecycle_packet"]
    assert outcome["outcome_type"] == "pending_intake_confirmed_lab"
    assert packet["target_draft_id"] == "golden-1"
    assert packet["terminal_state"] == "confirmed_lab_intake"
    assert packet["actual_intake_observed"] is True
    assert packet["meal_thread_mutated"] is False
    assert packet["ledger_entry_created"] is False
    assert second_turn["post_turn_action_state_delta"][
        "pending_intake_draft_ids_closed"
    ] == ["golden-1"]


def test_pending_intake_followup_cancel_closes_lab_draft_without_intake(
    tmp_path: Path,
) -> None:
    artifact = _session_with_pending_action(tmp_path, "cancel_pending_intake")

    assert artifact["status"] == "pass"
    assert artifact["lab_pending_intake_terminal_states"] == [
        "canceled_lab_intake"
    ]
    assert artifact["lab_action_state"]["active_pending_intake_draft_ids"] == []
    assert artifact["lab_action_state"]["active_pending_intake_source_refs"] == []

    second_turn = read_json_artifact(Path(artifact["turn_artifact_paths"][1]))
    [outcome] = second_turn["post_turn_chat_action_outcomes"]
    packet = outcome["pending_intake_lifecycle_packet"]
    assert outcome["outcome_type"] == "pending_intake_canceled_lab"
    assert packet["target_draft_id"] == "golden-1"
    assert packet["terminal_state"] == "canceled_lab_intake"
    assert packet["actual_intake_observed"] is False
    assert packet["canonical_product_mutation_allowed"] is False


def _session_with_pending_action(tmp_path: Path, action: str) -> dict[str, object]:
    return run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id=f"pending-intake-{action}",
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
                "turn_id": "t2-followup",
                "post_turn_chat_actions": [
                    {
                        "event_id": action,
                        "target_candidate_id": "pending_intake_followup:3",
                        "action": action,
                    }
                ],
            },
        ],
    )
