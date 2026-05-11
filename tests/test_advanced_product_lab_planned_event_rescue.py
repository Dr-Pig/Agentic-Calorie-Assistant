from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_planned_event_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_planned_event_all_day_fixture_inputs import (
    build_product_lab_planned_event_all_day_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_planned_event_rescue import (
    run_product_lab_planned_event_rescue,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)


LAB_MODE = "isolated_advanced_product_lab"


def test_planned_event_rescue_builds_lab_only_proposal_preview() -> None:
    artifact = run_product_lab_planned_event_rescue(
        fixture_inputs=build_product_lab_planned_event_fixture_inputs(),
        enabled=True,
    )

    assert artifact["artifact_type"] == (
        "advanced_product_lab_planned_event_rescue_runtime_artifact"
    )
    assert artifact["status"] == "pass"
    assert artifact["source_shadow_packet_status"] == "pass"
    assert artifact["proposal_card"]["card_kind"] == "planned_event_rescue_lab"
    assert artifact["proposal_card"]["event_label"] == "Saturday buffet"
    assert artifact["proposal_card"]["reserve_kcal"] == 800
    assert artifact["proposal_card"]["recommended_days"] == 4
    assert artifact["proposal_card"]["daily_kcal_adjustment"] == -200
    assert [
        row["local_date"] for row in artifact["proposal_card"]["overlay_preview_rows"]
    ] == ["2026-05-12", "2026-05-13", "2026-05-14", "2026-05-15"]
    assert artifact["primary_actions"] == [
        "accept_rescue_plan",
        "dismiss_rescue_plan",
    ]
    assert artifact["pending_rescue_commit_packet"]["status"] == "pass"
    assert artifact["proposal_presented_to_lab"] is True
    assert artifact["future_overlay_preview_only"] is True
    assert artifact["ledger_entry_created"] is False
    assert artifact["day_budget_mutated"] is False
    assert artifact["canonical_commit_requested"] is False


def test_product_lab_turn_surfaces_f2_planned_event_rescue_chat_packet() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode=LAB_MODE,
        turn=_planned_event_turn("f2-turn"),
        fixture_inputs=build_product_lab_planned_event_fixture_inputs(),
    )

    messages = artifact["lab_chat_surface"]["messages"]
    candidate_ids = [message["candidate_id"] for message in messages]
    planned = next(
        message for message in messages if message["candidate_id"] == "planned_event_rescue:0"
    )

    assert artifact["status"] == "pass"
    assert "rescue_nudge:1" not in candidate_ids
    assert planned["workflow_family"] == "rescue"
    assert "Saturday buffet" in planned["copy"]
    assert planned["rescue_proposal"]["proposal_card"]["card_kind"] == (
        "planned_event_rescue_lab"
    )
    assert planned["rescue_proposal"]["handoff_state"] == (
        "pending_user_rescue_commit_confirmation"
    )
    assert planned["rescue_proposal"]["canonical_commit_requested"] is False
    assert planned["canonical_mutation_requested"] is False
    assert artifact["product_lab_planned_event_rescue_artifact"]["status"] == "pass"
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["user_facing_behavior_changed"] is False


def test_product_lab_session_accepts_planned_event_as_pending_lab_commit(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="planned-event-accept-session",
        fixture_inputs=build_product_lab_planned_event_fixture_inputs(),
        turns=[
            {
                **_planned_event_turn("f2-accept"),
                "post_turn_chat_actions": [
                    {
                        "event_id": "accept-f2-rescue",
                        "target_candidate_id": "planned_event_rescue:0",
                        "action": "accept_rescue_plan",
                    }
                ],
            }
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_rescue_active_inbox_count"] == 0
    assert artifact["lab_rescue_history_statuses"] == [
        "accepted_pending_commit_confirmation"
    ]
    assert artifact["lab_action_state"]["rescue_commit_pending_count"] == 1
    [history] = artifact["lab_rescue_proposal_read_model"]["history_rows"]
    assert history["candidate_id"] == "planned_event_rescue:0"
    assert history["proposal_card"]["card_kind"] == "planned_event_rescue_lab"
    assert "200 kcal per day" in history["expandable_user_facing_explanation"]
    assert "rescue_proposal_card:planned_event_rescue_lab" in artifact[
        "lab_rescue_action_decision_source_refs"
    ]
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["durable_product_memory_written"] is False


def test_product_lab_session_runs_t_all_day_allocation_guidance_to_proposal(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="planned-event-all-day-session",
        fixture_inputs=build_product_lab_planned_event_all_day_fixture_inputs(),
        turns=[
            {
                "turn_id": "t-guidance",
                "semantic_intent_fixture": "planned_event_all_day_allocation",
                "planned_event_guidance_enabled": True,
            },
            {
                **_planned_event_turn("t-set-reserve"),
                "semantic_intent_fixture": "planned_event_all_day_allocation",
                "post_turn_chat_actions": [
                    {
                        "event_id": "accept-t-rescue",
                        "target_candidate_id": "planned_event_rescue:0",
                        "action": "accept_rescue_plan",
                    }
                ],
            },
        ],
    )

    assert artifact["status"] == "pass"
    first_turn = artifact["turn_summaries"][0]
    second_turn = artifact["turn_summaries"][1]
    assert first_turn["visible_candidate_ids"] == ["planned_event_guidance:0"]
    assert "planned_event_rescue:0" in second_turn["visible_candidate_ids"]
    assert "rescue_nudge:1" not in second_turn["visible_candidate_ids"]
    assert artifact["lab_rescue_history_statuses"] == [
        "accepted_pending_commit_confirmation"
    ]

    first_record = _read_turn_record(artifact, 0)
    [guidance] = first_record["turn_artifact"]["lab_chat_surface"]["messages"]
    assert guidance["candidate_id"] == "planned_event_guidance:0"
    assert guidance["planned_event_guidance"]["informational_only"] is True
    assert guidance["planned_event_guidance"]["proposal_created"] is False
    assert guidance["planned_event_guidance"]["suggested_reserve_kcal"] == 600
    assert guidance["planned_event_guidance"]["lunch_cap_kcal"] == 400
    assert guidance["canonical_mutation_requested"] is False

    [history] = artifact["lab_rescue_proposal_read_model"]["history_rows"]
    preview = history["proposal_card"]["overlay_preview_rows"]
    assert [row["local_date"] for row in preview] == [
        "2026-05-12",
        "2026-05-13",
        "2026-05-14",
        "2026-05-15",
    ]
    assert {row["proposed_rescue_overlay_kcal"] for row in preview} == {-200}
    assert {row["candidate_effective_budget_kcal"] for row in preview} == {1600}
    assert history["canonical_product_mutation_allowed"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["durable_product_memory_written"] is False


def test_product_lab_session_dismisses_planned_event_instance_to_history(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="planned-event-dismiss-session",
        fixture_inputs=build_product_lab_planned_event_fixture_inputs(),
        turns=[
            {
                **_planned_event_turn("f2-dismiss"),
                "post_turn_chat_actions": [
                    {
                        "event_id": "dismiss-f2-rescue",
                        "target_candidate_id": "planned_event_rescue:0",
                        "action": "dismiss_rescue_plan",
                    }
                ],
            }
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_rescue_active_inbox_count"] == 0
    assert artifact["lab_rescue_history_statuses"] == ["dismissed"]
    assert artifact["lab_action_state"]["dismissed_rescue_instance_count"] == 1
    [history] = artifact["lab_rescue_proposal_read_model"]["history_rows"]
    assert history["candidate_id"] == "planned_event_rescue:0"
    assert history["proposal_card"]["card_kind"] == "planned_event_rescue_lab"
    assert history["active_inbox_visible"] is False
    assert history["canonical_product_mutation_allowed"] is False


def _planned_event_turn(turn_id: str) -> dict[str, object]:
    return {
        "session_id": "lab-session-1",
        "turn_id": turn_id,
        "surface": "chat",
        "user_utterance": "fixture text is not a semantic oracle",
        "semantic_intent_fixture": "advanced_recommendation_rescue_proactive_loop",
        "planned_event_rescue_enabled": True,
    }


def _read_turn_record(artifact: dict[str, object], index: int) -> dict[str, object]:
    from app.shared.infra.json_artifacts import read_json_artifact

    return read_json_artifact(Path(artifact["turn_artifact_paths"][index]))  # type: ignore[index]
