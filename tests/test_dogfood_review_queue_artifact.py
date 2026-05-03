from __future__ import annotations

import json
from pathlib import Path

from app.composition.dogfood_review_queue import (
    build_dogfood_review_queue_artifact,
    build_review_candidate_from_runtime_trace,
)


def _unsupported_runtime_trace() -> dict:
    return {
        "trace_schema_version": "accurate_intake_conversation_turn_v1",
        "request_id": "turn-rescue-001",
        "user_message": {"raw_text": "我今天爆卡怎麼辦", "source": "chat"},
        "assistant_response": {"text": "這版先提供一般建議，不會建立救援計畫。"},
        "manager_decision": {
            "intent_type": "answer_only",
            "final_action": "answer_only",
            "unsupported_intent_family": "rescue",
        },
        "dogfood_trace_policy": {
            "lifecycle_status": "raw_trace",
            "raw_trace_is_truth": False,
            "unsupported_intent_policy": {
                "final_action": "answer_only",
                "answer_only_subtype": "general_guidance",
                "unsupported_intent_family": "rescue",
                "mutation_allowed": False,
            },
        },
        "trace_chain": {
            "evidence_required": False,
            "evidence_requirement_satisfied": True,
        },
        "final_mapping": {"final_action": "answer_only"},
    }


def test_review_candidate_artifact_marks_unsupported_trace_without_promoting_truth() -> None:
    candidate = build_review_candidate_from_runtime_trace(
        _unsupported_runtime_trace(),
        reviewer_agent_suggestion={
            "review_candidate": True,
            "likely_failure_family": "unsupported_intent",
            "confidence": 0.74,
        },
    )

    assert candidate["status"] == "review_candidate"
    assert candidate["trace_id"] == "turn-rescue-001"
    assert candidate["auto_flags"] == ["unsupported_intent"]
    assert candidate["raw_trace_is_truth"] is False
    assert candidate["review_candidate"]["reviewer_agent_can_approve"] is False
    assert candidate["canonical_eval_promotion"]["allowed"] is False
    assert candidate["canonical_eval_promotion"]["missing"] == [
        "human_approval",
        "product_semantic_source",
        "stable_expected_behavior",
        "regression_test_or_eval_registration",
    ]


def test_review_queue_artifact_is_local_only_and_preserves_correction_events_as_review_material() -> None:
    correction_event = {
        "trace_id": "turn-bento-correction",
        "event_type": "user_correction_feedback",
        "correction_type": "portion_correction",
        "review_status": "raw",
        "food_kb_truth_update_allowed": False,
        "canonical_eval_promotion_allowed": False,
    }

    artifact = build_dogfood_review_queue_artifact(
        review_candidates=[
            build_review_candidate_from_runtime_trace(_unsupported_runtime_trace()),
        ],
        correction_feedback_events=[correction_event],
    )

    assert artifact["artifact_schema_version"] == "1.0"
    assert artifact["claim_scope"] == "local_dogfood_review_queue_artifact"
    assert artifact["local_only"] is True
    assert artifact["contains_personal_diet_logs"] is True
    assert artifact["do_not_commit"] is True
    assert artifact["promotion_policy"]["raw_trace_can_be_canonical_eval_truth"] is False
    assert artifact["promotion_policy"]["human_approval_required_for_canonical_eval"] is True
    assert artifact["review_candidate_count"] == 1
    assert artifact["correction_feedback_event_count"] == 1
    assert artifact["correction_feedback_events"][0]["review_status"] == "raw"
    assert artifact["correction_feedback_events"][0]["food_kb_truth_update_allowed"] is False


def test_review_queue_builder_script_writes_artifact_from_runtime_trace(tmp_path: Path) -> None:
    trace_path = tmp_path / "runtime_trace.json"
    output_path = tmp_path / "review_queue.json"
    trace_path.write_text(json.dumps(_unsupported_runtime_trace(), ensure_ascii=False), encoding="utf-8")

    from scripts.build_accurate_intake_dogfood_review_queue import main

    exit_code = main(["--trace-json", str(trace_path), "--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["review_candidates"][0]["trace_id"] == "turn-rescue-001"
    assert artifact["review_candidates"][0]["auto_flags"] == ["unsupported_intent"]
    assert artifact["status"] == "generated"
