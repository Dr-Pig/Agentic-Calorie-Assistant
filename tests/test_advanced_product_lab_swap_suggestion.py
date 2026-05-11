from __future__ import annotations

import json
from pathlib import Path

from app.advanced_shadow_lab.product_lab_journey_coverage import (
    build_product_lab_journey_coverage_summary,
)
from app.advanced_shadow_lab.product_lab_memory import (
    empty_product_lab_memory_context_pack,
)
from app.advanced_shadow_lab.product_lab_recommendation import (
    run_product_lab_recommendation,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from app.advanced_shadow_lab.product_lab_swap_fixture_inputs import (
    build_product_lab_swap_fixture_inputs,
)
from app.shared.infra.json_artifacts import read_json_artifact


def test_swap_suggestion_recommendation_mode_uses_structured_high_kcal_fixture() -> None:
    artifact = run_product_lab_recommendation(
        turn=_swap_turn("s1-recommendation"),
        fixture_inputs=build_product_lab_swap_fixture_inputs(history_sufficient=True),
        memory_context_pack=empty_product_lab_memory_context_pack(
            session_id="swap-session",
            turn_id="s1-recommendation",
        ),
    )

    context = artifact["planning"]["recommendation_context_result"]
    swap = context["swap_suggestion"]
    packet = artifact["offer_synthesis"]["ux_packet"]["swap_suggestion_packet"]

    assert context["user_goal"] == "swap_suggestion"
    assert context["raw_user_text_semantic_inference_performed"] is False
    assert swap == {
        "mode": "swap_suggestion",
        "trigger_source": "structured_committed_item_fixture",
        "history_sufficient": True,
        "original_item_name": "Full-sugar milk tea",
        "original_kcal": 520,
        "suggested_item_name": "Half-sugar milk tea",
        "suggested_kcal": 380,
        "weekly_frequency_estimate": 7,
        "suggestion_basis": "preference_pattern",
        "source_refs": [
            "meal_item:full-sugar-milk-tea",
            "memory_candidate:half-sugar-milk-tea-1",
        ],
    }
    assert artifact["retrieval_guard_scoring"]["primary_candidate_id"] == (
        "half-sugar-milk-tea-1"
    )
    assert packet["kcal_saving_per_instance"] == 140
    assert packet["weekly_saving_estimate"] == 980
    assert packet["canonical_commit_requested"] is False
    assert artifact["durable_product_memory_written"] is False


def test_swap_suggestion_surfaces_standalone_lab_message_and_remember_action() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_swap_turn("s1-turn"),
        fixture_inputs=build_product_lab_swap_fixture_inputs(history_sufficient=True),
    )

    swap_messages = [
        message
        for message in artifact["lab_chat_surface"]["messages"]
        if message["candidate_id"] == "swap_suggestion:0"
    ]

    assert artifact["status"] == "pass"
    assert len(swap_messages) == 1
    swap = swap_messages[0]
    assert swap["workflow_family"] == "recommendation"
    assert swap["trigger_type"] == "swap_suggestion"
    assert swap["swap_suggestion"]["suggested_item_name"] == "Half-sugar milk tea"
    assert swap["swap_suggestion"]["kcal_saving_per_instance"] == 140
    assert [action["action"] for action in swap["actions"]] == [
        "dismiss",
        "snooze",
        "undo",
        "remember_memory",
    ]
    assert swap["canonical_mutation_requested"] is False
    assert swap["served_to_mainline_user"] is False


def test_swap_suggestion_does_not_trigger_for_cold_start_context() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_swap_turn("s1-cold-start"),
        fixture_inputs=build_product_lab_swap_fixture_inputs(history_sufficient=False),
    )

    assert artifact["status"] == "pass"
    assert [
        message
        for message in artifact["lab_chat_surface"]["messages"]
        if message["candidate_id"] == "swap_suggestion:0"
    ] == []
    assert artifact["product_lab_recommendation_artifact"]["offer_synthesis"][
        "ux_packet"
    ]["swap_suggestion_packet"] == {}


def test_swap_suggestion_remember_action_promotes_isolated_lab_memory(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="swap-memory-session",
        fixture_inputs=build_product_lab_swap_fixture_inputs(history_sufficient=True),
        turns=[
            {
                "turn_id": "s1-swap",
                "turn_mode": "swap_suggestion",
                "lab_now_minute": 10,
                "post_turn_memory_action_events": [
                    {
                        "event_id": "remember-swap-milk-tea",
                        "action": "remember_memory",
                        "target_candidate_id": "swap_suggestion:0",
                        "signal_type": "explicit_preference",
                        "summary": "Prefer the half-sugar milk tea swap.",
                        "original_item_name": "Full-sugar milk tea",
                        "suggested_item_name": "Half-sugar milk tea",
                        "kcal_saving_per_instance": 140,
                        "intended_consumers": ["recommendation", "proactive"],
                        "raw_user_utterance": "RAW SWAP MEMORY SHOULD NOT LEAK",
                    }
                ],
                "post_turn_memory_review_decisions": [
                    _decision("remember-swap-milk-tea")
                ],
            },
            {"turn_id": "s2-use-swap-memory", "lab_now_minute": 20},
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_memory_record_ids"] == ["remember-swap-milk-tea"]
    assert artifact["lab_memory_context_injected"] is True
    assert artifact["durable_product_memory_written"] is False

    t1 = read_json_artifact(Path(artifact["turn_artifact_paths"][0]))
    t2 = read_json_artifact(Path(artifact["turn_artifact_paths"][1]))["turn_artifact"]
    pipeline = t1["memory_pipeline_artifact"]

    assert pipeline["action_signal_artifact"]["derived_signal_count"] == 1
    assert pipeline["promotion_artifact"]["promoted_record_ids"] == [
        "remember-swap-milk-tea"
    ]
    assert t2["lab_memory_context_pack"]["selected_record_ids"] == [
        "remember-swap-milk-tea"
    ]
    assert "RAW SWAP MEMORY SHOULD NOT LEAK" not in json.dumps(
        artifact, ensure_ascii=False
    )


def test_journey_coverage_moves_s_after_swap_suggestion_evidence() -> None:
    summary = build_product_lab_journey_coverage_summary({})

    assert "S" in summary["covered_by_existing_executable_evidence_journey_ids"]
    assert summary["product_capability_gap_journey_ids"] == []
    assert summary["next_product_capability_slice"] == ""


def _swap_turn(turn_id: str) -> dict[str, object]:
    return {
        "session_id": "swap-session",
        "turn_id": turn_id,
        "surface": "chat",
        "semantic_intent_fixture": "swap_suggestion",
        "turn_mode": "swap_suggestion",
        "user_utterance": "fixture text is not a semantic oracle",
    }


def _decision(candidate_id: str) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "decision": "promote",
        "confirmed": True,
        "reviewer": "lab-human",
        "reason": "confirmed_for_swap_lab",
    }
