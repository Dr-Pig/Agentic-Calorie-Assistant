from __future__ import annotations

import json
from pathlib import Path

from app.composition.dogfood_review_queue import (
    build_dogfood_review_queue_artifact,
    build_feedback_record_from_desktop_capture,
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


def test_desktop_feedback_capture_is_trace_linked_local_triage_not_product_truth() -> None:
    feedback = build_feedback_record_from_desktop_capture(
        category="nutrition_estimate",
        feedback_text="The bubble tea estimate looked too low.",
        page="chat",
        selected_date="2026-05-10",
        user_external_id="local-self-use-001",
        trace_id="trace-bubble-tea",
        message_id="assistant-message-9",
        severity="medium",
        ui_event={"route": "/static/accurate-intake-chat.html", "api_duration_ms": 1234},
    )

    assert feedback["artifact_type"] == "accurate_intake_dogfood_feedback_record"
    assert feedback["status"] == "captured"
    assert feedback["claim_scope"] == "local_dogfood_feedback_triage_record"
    assert feedback["local_only"] is True
    assert feedback["contains_personal_diet_logs"] is True
    assert feedback["do_not_commit"] is True
    assert feedback["category"] == "nutrition_estimate"
    assert feedback["feedback_text"] == "The bubble tea estimate looked too low."
    assert feedback["linked_context"] == {
        "page": "chat",
        "selected_date": "2026-05-10",
        "user_external_id": "local-self-use-001",
        "trace_id": "trace-bubble-tea",
        "message_id": "assistant-message-9",
        "meal_id": None,
    }
    assert feedback["ui_event"]["route"] == "/static/accurate-intake-chat.html"
    assert feedback["frontend_semantic_owner"] is False
    assert feedback["mutation_authority"] is False
    assert feedback["manager_context_injection_allowed"] is False
    assert feedback["food_kb_truth_update_allowed"] is False
    assert feedback["canonical_eval_promotion_allowed"] is False


def test_review_queue_artifact_preserves_desktop_feedback_records_without_promotion() -> None:
    feedback = build_feedback_record_from_desktop_capture(
        category="ui_ux",
        feedback_text="Date switching was hard to notice.",
        page="today",
        selected_date="2026-05-10",
        user_external_id="local-self-use-001",
        trace_id=None,
    )

    artifact = build_dogfood_review_queue_artifact(
        review_candidates=[],
        desktop_feedback_records=[feedback],
    )

    assert artifact["feedback_triage_record_count"] == 1
    assert artifact["desktop_feedback_records"][0]["category"] == "ui_ux"
    assert artifact["promotion_policy"]["feedback_can_create_product_truth"] is False
    assert artifact["promotion_policy"]["feedback_can_create_fooddb_truth"] is False
    assert artifact["promotion_policy"]["feedback_can_create_eval_truth"] is False


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


def test_review_queue_builder_script_captures_browser_realistic_evidence_gap(
    tmp_path: Path,
) -> None:
    diagnostic_path = tmp_path / "browser_realistic.json"
    output_path = tmp_path / "review_queue.json"
    diagnostic_path.write_text(
        json.dumps(
            {
                "artifact_type": "accurate_intake_browser_realistic_web_dogfood_v2",
                "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
                "summary": {
                    "evidence_gap_observed": True,
                    "manager_context_status": "present",
                },
                "fixture_evidence_used": True,
                "fooddb_evidence_used": False,
                "real_fooddb_pass_claimed": False,
                "dogfood_pass": False,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    from scripts.build_accurate_intake_dogfood_review_queue import main

    exit_code = main(
        [
            "--diagnostic-json",
            str(diagnostic_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "generated"
    assert artifact["review_candidate_count"] == 1
    candidate = artifact["review_candidates"][0]
    assert candidate["trace_id"] == "accurate_intake_browser_realistic_web_dogfood_v2"
    assert candidate["auto_flags"] == ["evidence_gap"]
    assert candidate["raw_trace"]["raw_trace_is_truth"] is False
    assert candidate["canonical_eval_promotion"]["allowed"] is False
    assert candidate["review_candidate"]["reviewer_agent_can_approve"] is False


def test_review_queue_builder_script_ingests_desktop_feedback_jsonl(
    tmp_path: Path,
) -> None:
    feedback = build_feedback_record_from_desktop_capture(
        category="latency",
        feedback_text="The turn took too long.",
        page="chat",
        selected_date="2026-05-10",
        user_external_id="local-self-use-001",
        trace_id="trace-latency-001",
    )
    feedback_jsonl = tmp_path / "feedback.jsonl"
    output_path = tmp_path / "review_queue.json"
    feedback_jsonl.write_text(json.dumps(feedback, ensure_ascii=False) + "\n", encoding="utf-8")

    from scripts.build_accurate_intake_dogfood_review_queue import main

    exit_code = main(
        [
            "--desktop-feedback-jsonl",
            str(feedback_jsonl),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["feedback_triage_record_count"] == 1
    assert artifact["desktop_feedback_records"][0]["category"] == "latency"
    assert artifact["promotion_policy"]["feedback_can_create_product_truth"] is False


def test_self_use_runbook_documents_desktop_feedback_capture_path() -> None:
    runbook = Path("docs/quality/ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md").read_text(
        encoding="utf-8-sig"
    )

    assert "/static/accurate-intake-feedback.html" in runbook
    assert "/accurate-intake/feedback" in runbook
    assert "--desktop-feedback-jsonl" in runbook
    assert "workspace_data/local_dogfood_feedback" in runbook
