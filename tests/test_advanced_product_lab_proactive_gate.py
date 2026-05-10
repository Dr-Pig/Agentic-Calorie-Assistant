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


def test_product_lab_proactive_skips_unqualified_recommendation_before_chat() -> None:
    from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive
    from app.advanced_shadow_lab.product_lab_recommendation import (
        run_product_lab_recommendation,
    )
    from app.advanced_shadow_lab.product_lab_rescue import run_product_lab_rescue

    fixture_inputs = _generic_only_fixture_inputs()
    recommendation = run_product_lab_recommendation(
        turn=_turn("lab-turn-unqualified-recommendation"),
        fixture_inputs=fixture_inputs,
        memory_context_pack={},
    )
    artifact = run_product_lab_proactive(
        turn=_turn("lab-turn-unqualified-recommendation"),
        fixture_inputs=fixture_inputs,
        memory_context_pack={},
        recommendation_artifact=recommendation,
        rescue_artifact=run_product_lab_rescue(fixture_inputs=fixture_inputs),
    )

    assert artifact["status"] == "pass"
    assert recommendation["recommendation_served_to_lab"] is False
    assert recommendation["retrieval_guard_scoring"]["pool_decision"] == (
        "silent_no_qualified_candidate"
    )
    assert [candidate["trigger_type"] for candidate in artifact["candidates"]] == [
        "rescue_nudge"
    ]
    assert [
        review["trigger_type"]
        for review in artifact["pre_delivery_review"]["candidate_reviews"]
    ] == ["rescue_nudge"]
    assert artifact["delivery_packet"]["candidate_ids"] == ["rescue_nudge"]


def _visible_by_turn(artifact: dict[str, object]) -> dict[str, list[str]]:
    return {
        row["turn_id"]: row["visible_candidate_ids"]
        for row in artifact["turn_summaries"]  # type: ignore[index]
    }


def _generic_only_fixture_inputs() -> dict[str, object]:
    fixture_inputs = _fixture_inputs()
    payload = fixture_inputs["recommendation_payload"]  # type: ignore[index]
    payload["candidate_source_fixture"] = [  # type: ignore[index]
        {
            "candidate_id": "generic-1",
            "title": "Something light nearby",
            "source_type": "safe_fallback",
            "estimated_kcal": 350,
            "estimated_kcal_range": {"min": 280, "max": 350},
            "item_patterns": ["light_meal"],
            "hard_avoid_flags": [],
            "source_refs": ["fixture:generic-1"],
            "evidence_posture": "generic",
            "availability_posture": "likely",
            "realistic_executable": True,
            "user_accessible": True,
        }
    ]
    payload["negative_preference_summary"] = {"items": []}  # type: ignore[index]
    payload["open_rescue_context"] = {"accepted_conflict_patterns": []}  # type: ignore[index]
    return fixture_inputs
