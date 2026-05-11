from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_calibration import (
    run_product_lab_calibration,
)
from app.advanced_shadow_lab.product_lab_calibration_fixture_inputs import (
    build_product_lab_calibration_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from app.shared.infra.json_artifacts import read_json_artifact


def test_product_lab_calibration_builds_body_trend_proposal() -> None:
    artifact = run_product_lab_calibration(
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        enabled=True,
    )

    assert artifact["artifact_type"] == "advanced_product_lab_calibration_runtime_artifact"
    assert artifact["status"] == "pass"
    assert artifact["proposal_presented_to_lab"] is True
    assert artifact["calibration_confidence"] == "high"
    assert artifact["proposal_family"] == "budget_adjustment"
    assert artifact["activation_flags"] == {
        "lab_user_facing_behavior_changed": True,
        "served_to_mainline_user": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "production_scheduler_delivery_allowed": False,
        "manager_context_packet_changed": False,
    }

    card = artifact["proposal_card"]
    assert card["card_kind"] == "calibration_proposal_lab"
    assert card["trend_evidence"] == {
        "observation_window_days": 21,
        "body_observation_count": 9,
        "intake_coverage": 0.93,
        "operating_expenditure_shift_kcal": -340,
    }
    assert card["previous_daily_budget_kcal"] == 1800
    assert card["proposed_daily_budget_kcal"] == 1600
    assert card["daily_budget_delta_kcal"] == -200
    assert card["primary_actions"] == [
        "accept_calibration_proposal",
        "dismiss_calibration_proposal",
    ]


def test_product_lab_calibration_omits_proposal_when_data_is_insufficient() -> None:
    artifact = run_product_lab_calibration(
        fixture_inputs=build_product_lab_calibration_fixture_inputs(
            insufficient_data=True
        ),
        enabled=True,
    )

    assert artifact["status"] == "pass"
    assert artifact["proposal_presented_to_lab"] is False
    assert artifact["omission_reason"] == "calibration_posture_insufficient_data"
    assert artifact["proposal_card"] == {}
    assert artifact["activation_flags"]["lab_user_facing_behavior_changed"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def test_product_lab_turn_surfaces_calibration_chat_proposal_only() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_calibration_turn("calibration-turn-1"),
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
    )

    assert artifact["status"] == "pass"
    messages = artifact["lab_chat_surface"]["messages"]
    assert [message["workflow_family"] for message in messages] == ["calibration"]
    assert [message["candidate_id"] for message in messages] == [
        "calibration_proposal:0"
    ]

    proposal = messages[0]["calibration_proposal"]
    assert proposal["proposal_card"]["card_kind"] == "calibration_proposal_lab"
    assert proposal["primary_actions"] == [
        "accept_calibration_proposal",
        "dismiss_calibration_proposal",
    ]
    assert proposal["lab_body_plan_preview"]["daily_budget_kcal"] == 1600
    assert messages[0]["canonical_mutation_requested"] is False
    assert artifact["product_lab_calibration_artifact"]["proposal_presented_to_lab"] is True


def test_product_lab_session_accepts_calibration_as_lab_only_plan_effect(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="lab-session-calibration-accept",
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=[
            {
                **_calibration_turn("t1-calibration"),
                "post_turn_chat_actions": [
                    {
                        "event_id": "accept-calibration",
                        "target_candidate_id": "calibration_proposal:0",
                        "action": "accept_calibration_proposal",
                    }
                ],
            }
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_calibration_action_decision_count"] == 1
    assert artifact["lab_calibration_effect_applied_count"] == 1
    assert artifact["lab_calibration_latest_daily_budget_kcal"] == 1600
    assert artifact["lab_calibration_action_decision_kinds"] == [
        "apply_calibration_effect_lab"
    ]
    assert artifact["canonical_product_mutation_allowed"] is False

    [turn_path] = [Path(path) for path in artifact["turn_artifact_paths"]]
    outcome = read_json_artifact(turn_path)["post_turn_chat_action_outcomes"][0]
    packet = outcome["calibration_action_decision_packet"]
    assert packet["lab_body_plan_after"]["daily_budget_kcal"] == 1600
    assert packet["canonical_product_mutation_allowed"] is False
    assert "calibration_proposal_card:budget_adjustment" in packet["source_refs"]


def test_product_lab_session_dismisses_calibration_without_lab_plan_effect(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="lab-session-calibration-dismiss",
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=[
            {
                **_calibration_turn("t1-calibration"),
                "post_turn_chat_actions": [
                    {
                        "event_id": "dismiss-calibration",
                        "target_candidate_id": "calibration_proposal:0",
                        "action": "dismiss_calibration_proposal",
                    }
                ],
            }
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_calibration_action_decision_count"] == 1
    assert artifact["lab_calibration_effect_applied_count"] == 0
    assert artifact["lab_calibration_dismissed_count"] == 1
    assert artifact["lab_calibration_latest_daily_budget_kcal"] == 1800
    assert artifact["lab_calibration_action_decision_kinds"] == [
        "dismiss_calibration_proposal_lab"
    ]
    assert artifact["canonical_product_mutation_allowed"] is False


def _calibration_turn(turn_id: str) -> dict[str, object]:
    return {
        "session_id": "lab-session-calibration",
        "turn_id": turn_id,
        "surface": "chat",
        "user_utterance": "fixture text is not a semantic oracle",
        "semantic_intent_fixture": "calibration_proposal_from_body_trend",
        "calibration_enabled": True,
    }
