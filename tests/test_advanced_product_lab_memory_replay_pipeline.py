from __future__ import annotations

import json
from pathlib import Path

from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from app.shared.infra.json_artifacts import read_json_artifact
from tests.test_advanced_product_lab_runtime import _fixture_inputs


def test_product_lab_session_replay_promotes_memory_signals_through_review_pipeline(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="memory-pipeline-session",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-signal",
                "lab_now_minute": 10,
                "post_turn_memory_signal_events": [
                    _signal(
                        "golden-oatmeal",
                        "golden_order",
                        "Morning Bar oatmeal is reliable.",
                        store_name="Morning Bar",
                        item_names=["oatmeal"],
                        estimated_kcal=420,
                    ),
                    _signal(
                        "negative-cilantro",
                        "negative_preference",
                        "Avoid cilantro in recommendations.",
                        blocks_candidate_types=["recommendation_candidate"],
                        intended_consumers=["recommendation"],
                    ),
                ],
                "post_turn_memory_review_decisions": [
                    _decision("golden-oatmeal"),
                    _decision("negative-cilantro"),
                ],
            },
            {"turn_id": "t2-use-memory", "lab_now_minute": 20},
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_memory_record_ids"] == [
        "golden-oatmeal",
        "negative-cilantro",
    ]
    assert artifact["lab_memory_context_injected"] is True
    assert artifact["durable_product_memory_written"] is False

    turn_paths = [Path(path) for path in artifact["turn_artifact_paths"]]
    t1 = read_json_artifact(turn_paths[0])
    t2 = read_json_artifact(turn_paths[1])["turn_artifact"]
    pipeline = t1["memory_pipeline_artifact"]

    assert pipeline["pipeline_path"] == "candidate_review_promotion"
    assert pipeline["extraction_artifact"]["candidate_count"] == 2
    assert pipeline["review_queue"]["review_item_count"] == 2
    assert pipeline["promotion_artifact"]["promoted_record_ids"] == [
        "golden-oatmeal",
        "negative-cilantro",
    ]
    assert t2["lab_memory_context_pack"]["selected_record_ids"] == [
        "golden-oatmeal",
        "negative-cilantro",
    ]
    assert "RAW SHOULD NOT LEAK" not in json.dumps(artifact, ensure_ascii=False)


def test_product_lab_session_replay_promotes_explicit_memory_action_signals(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="memory-action-session",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-action-signal",
                "lab_now_minute": 10,
                "post_turn_memory_action_events": [
                    {
                        "event_id": "remember-oatmeal-golden",
                        "action": "remember_memory",
                        "target_candidate_id": "recommendation_prompt:0",
                        "signal_type": "golden_order",
                        "summary": "Morning Bar oatmeal is reliable.",
                        "store_name": "Morning Bar",
                        "item_names": ["oatmeal"],
                        "estimated_kcal": 420,
                        "intended_consumers": ["recommendation", "proactive"],
                        "raw_user_utterance": "RAW MEMORY ACTION SHOULD NOT LEAK",
                    }
                ],
                "post_turn_memory_review_decisions": [
                    _decision("remember-oatmeal-golden")
                ],
            },
            {"turn_id": "t2-use-action-memory", "lab_now_minute": 20},
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_memory_record_ids"] == ["remember-oatmeal-golden"]
    assert artifact["lab_memory_context_injected"] is True
    assert artifact["durable_product_memory_written"] is False

    turn_paths = [Path(path) for path in artifact["turn_artifact_paths"]]
    t1 = read_json_artifact(turn_paths[0])
    t2 = read_json_artifact(turn_paths[1])["turn_artifact"]
    pipeline = t1["memory_pipeline_artifact"]
    action_signals = pipeline["action_signal_artifact"]

    assert pipeline["pipeline_path"] == "candidate_review_promotion"
    assert action_signals["derived_signal_count"] == 1
    assert action_signals["raw_user_text_semantic_inference_performed"] is False
    assert pipeline["extraction_artifact"]["memory_candidates"][0]["candidate_id"] == (
        "remember-oatmeal-golden"
    )
    assert pipeline["promotion_artifact"]["promoted_record_ids"] == [
        "remember-oatmeal-golden"
    ]
    assert t2["lab_memory_context_pack"]["selected_record_ids"] == [
        "remember-oatmeal-golden"
    ]
    assert "RAW MEMORY ACTION SHOULD NOT LEAK" not in json.dumps(
        artifact, ensure_ascii=False
    )


def test_product_lab_session_replay_does_not_turn_rescue_dismiss_into_memory_signal(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="memory-dismiss-session",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-dismiss-rescue",
                "post_turn_chat_actions": [
                    {
                        "event_id": "dismiss-rescue",
                        "target_candidate_id": "rescue_nudge:1",
                        "action": "dismiss_rescue_plan",
                    }
                ],
            },
            {"turn_id": "t2-after-dismiss", "lab_now_minute": 20},
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_memory_record_ids"] == []
    assert artifact["lab_memory_store_written"] is False
    assert artifact["lab_action_state"]["dismissed_rescue_instance_count"] == 1

    first_turn = read_json_artifact(Path(artifact["turn_artifact_paths"][0]))
    pipeline = first_turn["memory_pipeline_artifact"]
    assert pipeline["pipeline_path"] == "direct_memory_event_write"
    assert pipeline["action_signal_artifact"]["derived_signal_count"] == 0
    assert pipeline["lab_memory_store_written"] is False
    assert pipeline["durable_product_memory_written"] is False


def _signal(
    signal_id: str,
    signal_type: str,
    summary: str,
    **payload: object,
) -> dict[str, object]:
    return {
        "signal_id": signal_id,
        "signal_type": signal_type,
        "summary": summary,
        "source_object_refs": [f"turn:t1-signal:{signal_id}"],
        "raw_user_utterance": "RAW SHOULD NOT LEAK",
        **payload,
    }


def _decision(candidate_id: str) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "decision": "promote",
        "confirmed": True,
        "reviewer": "lab-human",
        "reason": "confirmed_for_lab",
    }
