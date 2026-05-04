from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_context_review import (
    build_context_review_artifact,
)


def _trace_with_context() -> dict:
    return {
        "request_id": "turn-context-present",
        "context_policy_version": "accurate_intake_mvp_context_policy_v1",
        "loaded_context_summary": {
            "recent_chat_messages": 4,
            "pending_followup_present": True,
            "pending_draft_present": False,
            "target_candidate_count": 2,
        },
        "omitted_context_summary": {
            "recent_chat_messages_omitted": 1,
            "policy_excluded_context_ids": [
                "debug_artifacts",
                "dogfood_review_artifacts",
                "raw_trace_dump",
                "food_gap_candidates_as_truth",
                "full_day_transcript_by_default",
                "long_term_memory",
                "proactive_context",
                "rescue_context",
                "recommendation_context",
            ],
        },
        "manager_context_packet_v1": {
            "hard_pins": {
                "pending_followup": {"runtime_turn_id": "turn-ask"},
                "pending_draft": None,
            },
            "target_candidates": {
                "for_correction_or_removal": [
                    {"meal_item_id": 1, "display_name": "tofu", "read_only": True},
                    {"meal_item_id": 2, "display_name": "rice", "read_only": True},
                ],
                "mutation_authority": False,
            },
        },
    }


def test_context_review_artifact_summarizes_present_and_missing_ce_fields() -> None:
    artifact = build_context_review_artifact(
        traces=[
            _trace_with_context(),
            {"request_id": "turn-context-missing"},
        ]
    )

    assert artifact["artifact_type"] == "accurate_intake_context_review_artifact"
    assert artifact["status"] == "generated"
    assert artifact["claim_scope"] == "local_context_review_diagnostic"
    assert artifact["local_only"] is True
    assert artifact["diagnostic_only"] is True
    assert artifact["context_engineering_fault_claimed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False

    present = artifact["trace_reviews"][0]
    assert present["status"] == "present"
    assert present["context_policy_version"] == "accurate_intake_mvp_context_policy_v1"
    assert present["loaded_context_summary_present"] is True
    assert present["omitted_context_summary_present"] is True
    assert present["pending_followup_present"] is True
    assert present["pending_draft_present"] is False
    assert present["target_candidate_count"] == 2
    assert present["forbidden_context_detected"] is False

    missing = artifact["trace_reviews"][1]
    assert missing["status"] == "not_available"
    assert missing["context_policy_version"] == "not_available"
    assert missing["loaded_context_summary_present"] is False
    assert missing["omitted_context_summary_present"] is False
    assert missing["target_candidate_count"] == 0


def test_context_review_artifact_detects_forbidden_context_without_fault_claim() -> None:
    trace = _trace_with_context()
    trace["long_term_memory"] = {"favorite": "latte"}

    artifact = build_context_review_artifact(traces=[trace])

    review = artifact["trace_reviews"][0]
    assert review["forbidden_context_detected"] is True
    assert review["forbidden_context_ids"] == ["long_term_memory"]
    assert artifact["summary"]["forbidden_context_trace_count"] == 1
    assert artifact["context_engineering_fault_claimed"] is False


def test_context_review_builder_script_writes_artifact(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.json"
    output_path = tmp_path / "context_review.json"
    trace_path.write_text(json.dumps(_trace_with_context(), ensure_ascii=False), encoding="utf-8")

    from scripts.build_accurate_intake_context_review_artifact import main

    exit_code = main(["--trace-json", str(trace_path), "--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "generated"
    assert artifact["trace_reviews"][0]["status"] == "present"
