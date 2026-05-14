from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from app.shared.infra.json_artifacts import read_json_artifact
from tests.test_advanced_product_lab_runtime import _fixture_inputs


def test_chat_dismiss_control_projects_shared_feedback_event(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="feedback-projection-dismiss",
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
            }
        ],
    )

    assert artifact["status"] == "pass"
    first_turn = read_json_artifact(Path(artifact["turn_artifact_paths"][0]))
    [entry] = first_turn["post_turn_control_state"]["journal_entries"]

    assert entry["feedback_event"] == {
        "target_type": "proactive_candidate",
        "target_id": "recommendation_prompt:0",
        "action": "dismiss",
        "reason": "too_frequent",
        "snooze_until": None,
        "source_turn_id": "t1-dismiss",
        "scope_keys": {
            "user_id": "advanced_product_lab_user",
            "workspace_id": "advanced_product_lab_workspace",
            "project_id": "advanced-product-lab",
            "surface": "chat",
        },
    }
    projection = entry["feedback_event_projection"]
    assert projection["status"] == "pass"
    assert projection["consumer_projections"][0]["projection_type"] == (
        "user_control_suppression"
    )
    assert projection["confirmed_memory_promoted"] is False
    assert projection["proactive_delivery_enabled"] is False
    assert projection["durable_product_memory_written"] is False
    assert entry["feedback_event_role"] == "audit_input_only"


def test_chat_opt_out_projects_suppression_and_memory_candidates(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="feedback-projection-opt-out",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-opt-out",
                "lab_now_minute": 10,
                "post_turn_chat_actions": [
                    {
                        "event_id": "opt-out-rec-chat",
                        "target_candidate_id": "recommendation_prompt:0",
                        "action": "opt_out",
                        "scope": "trigger_family",
                        "dismiss_reason": "too_frequent",
                        "next_signal_required": "user_reopens_recommendation_prompts",
                    }
                ],
            },
            {"turn_id": "t2-after-opt-out", "lab_now_minute": 20},
        ],
    )

    assert artifact["status"] == "pass"
    assert _visible_by_turn(artifact) == {
        "t1-opt-out": ["recommendation_prompt:0", "rescue_nudge:1"],
        "t2-after-opt-out": ["rescue_nudge:1"],
    }
    first_turn = read_json_artifact(Path(artifact["turn_artifact_paths"][0]))
    [entry] = first_turn["post_turn_control_state"]["journal_entries"]
    projection_types = {
        item["projection_type"]
        for item in entry["feedback_event_projection"]["consumer_projections"]
    }

    assert entry["feedback_event"]["action"] == "opt_out"
    assert projection_types == {
        "proactive_suppression_candidate",
        "app_use_memory_candidate",
    }
    assert entry["feedback_event_projection"]["durable_product_memory_written"] is False
    assert entry["feedback_event_projection_ready"] is True


def _visible_by_turn(artifact: dict[str, object]) -> dict[str, list[str]]:
    return {
        row["turn_id"]: row["visible_candidate_ids"]
        for row in artifact["turn_summaries"]  # type: ignore[index]
    }
