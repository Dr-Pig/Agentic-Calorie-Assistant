from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from app.shared.infra.json_artifacts import read_json_artifact
from tests.test_advanced_product_lab_runtime import _fixture_inputs, _turn


def test_product_lab_proactive_gate_suppresses_quiet_hours_before_chat() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn={
            **_turn("lab-turn-quiet-hours"),
            "proactive_gate_context": {"local_time": "23:15"},
        },
        fixture_inputs=_fixture_inputs(),
    )

    proactive = artifact["product_lab_proactive_artifact"]
    assert proactive["status"] == "pass"
    assert proactive["candidate_count"] == 0
    assert proactive["pre_delivery_review_summary"]["review_decision_counts"] == {
        "suppressed_context_or_data": 2
    }
    assert [trace["trigger_type"] for trace in proactive["omission_traces"]] == [
        "recommendation_prompt",
        "rescue_nudge",
    ]
    assert {
        trace["omission_reason"] for trace in proactive["omission_traces"]
    } == {"quiet_hours"}
    assert proactive["delivery_packet"]["chat_delivery_allowed"] is False
    assert artifact["lab_chat_surface"]["visible_message_count"] == 0
    assert artifact["lab_chat_response_packet"]["visible_chat_packets"] == []
    assert artifact["canonical_product_mutation_allowed"] is False


def test_product_lab_proactive_gate_records_permission_suppression() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn={
            **_turn("lab-turn-permission"),
            "proactive_gate_context": {
                "explicit_consent_ready_by_trigger": {"rescue_nudge": False}
            },
        },
        fixture_inputs=_fixture_inputs(),
    )

    proactive = artifact["product_lab_proactive_artifact"]
    assert proactive["status"] == "pass"
    assert [candidate["trigger_type"] for candidate in proactive["candidates"]] == [
        "recommendation_prompt"
    ]
    assert proactive["pre_delivery_review_summary"]["review_decision_counts"] == {
        "candidate_for_human_review": 1,
        "suppressed_permission": 1,
    }
    [trace] = proactive["omission_traces"]
    assert trace["trigger_type"] == "rescue_nudge"
    assert trace["omission_reason"] == "permission_explicit_consent_required"
    assert trace["review_decision"]["status"] == "suppressed_permission"
    assert [message["candidate_id"] for message in artifact["lab_chat_surface"]["messages"]] == [
        "recommendation_prompt:0"
    ]


def test_product_lab_proactive_gate_consumes_chat_control_journal(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="lab-session-proactive-control-gate",
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
    assert _visible_by_turn(artifact) == {
        "t1-dismiss": ["recommendation_prompt:0", "rescue_nudge:1"],
        "t2-after-dismiss": ["rescue_nudge:1"],
    }

    second_turn = read_json_artifact(Path(artifact["turn_artifact_paths"][1]))
    proactive = second_turn["turn_artifact"]["product_lab_proactive_artifact"]
    assert [candidate["trigger_type"] for candidate in proactive["candidates"]] == [
        "rescue_nudge"
    ]
    [trace] = proactive["omission_traces"]
    assert trace["trigger_type"] == "recommendation_prompt"
    assert trace["omission_reason"] == "dismissed_until_material_signal"
    assert trace["review_decision"]["status"] == "suppressed_feedback"
    assert trace["active_control_event_id"] == "dismiss-rec-chat"


def _visible_by_turn(artifact: dict[str, object]) -> dict[str, list[str]]:
    return {
        row["turn_id"]: row["visible_candidate_ids"]
        for row in artifact["turn_summaries"]  # type: ignore[index]
    }
