from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _candidate_trace() -> dict:
    return {
        "request_id": "rt-lab-candidate-001",
        "trace_meta": {
            "request_id": "rt-lab-candidate-001",
            "user_id": "user-a",
            "bundle": "intake_execution",
            "local_date": "2026-05-09",
        },
        "memory_lab_scope": {
            "workspace_id": "workspace-a",
            "project_id": "advanced-memory-runtime-lab",
            "surface": "manager_runtime_lab",
            "run_id": "candidate-run-001",
        },
        "request": {
            "user_id": "user-a",
            "local_date": "2026-05-09",
            "text": "structured signal carries the memory candidate",
            "allow_search": False,
        },
        "manager_final_decision": {
            "intent": "log_meal",
            "workflow_effect": "commit_meal_log",
        },
        "memory_lab_candidate_signal": {
            "candidate_type": "preference",
            "manager_decision_field": "memory_candidate_requested",
            "source_refs": ["message:dogfood-preference-001"],
            "review_status": "pending",
            "promotion_allowed_now": False,
            "human_review_required": True,
            "reason_codes": ["explicit_user_preference"],
        },
    }


def test_candidate_extraction_golden_suite_matches_expected_case_outcomes() -> None:
    from app.memory.application.runtime_lab_candidate_extraction import (
        build_candidate_extraction_artifact_from_edd_suite,
    )
    from app.memory.application.runtime_lab_memory_edd import (
        load_runtime_lab_memory_edd_suite,
    )

    suite = load_runtime_lab_memory_edd_suite()
    artifact = build_candidate_extraction_artifact_from_edd_suite(suite)

    assert artifact["artifact_type"] == "runtime_lab_memory_candidate_extraction"
    assert artifact["status"] == "pass"
    assert artifact["candidate_count"] == 7
    assert artifact["rejection_count"] == 3
    assert artifact["runtime_connected"] is False
    assert artifact["lab_isolated"] is True
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["manager_context_packet_changed"] is False

    by_case = {item["case_id"]: item for item in artifact["case_results"]}
    assert by_case["explicit_preference_confirm_candidate"]["candidate_type"] == "preference"
    assert by_case["negative_preference_blocks_recommendation_candidate"][
        "candidate_type"
    ] == "negative_preference"
    assert by_case["temporary_preference_expires_without_confirmed_memory"][
        "candidate_type"
    ] == "temporary_preference"
    assert by_case["repeated_item_pattern_candidate_only"]["candidate_type"] == "pattern"
    assert by_case["golden_order_materialized_from_history"][
        "candidate_type"
    ] == "golden_order"
    assert by_case["ignored_proactive_creates_suppression_signal"][
        "candidate_type"
    ] == "interaction_preference"
    assert by_case["stale_conflicting_pattern_requires_review"][
        "candidate_type"
    ] == "contradiction_review"
    assert by_case["correction_updates_canonical_not_memory"]["outcome"] == "rejected"
    assert by_case["missing_scope_rejects_memory_use"]["rejection_reason"] == (
        "missing_scope_keys"
    )
    assert by_case["prompt_injection_cannot_create_memory"]["rejection_reason"] == (
        "untrusted_instruction_attempt"
    )

    for candidate in artifact["candidates"]:
        assert candidate["review_status"] == "pending"
        assert candidate["promotion_allowed_now"] is False
        assert candidate["runtime_effect_allowed"] is False
        assert candidate["human_review_required"] is True
        assert candidate["source_object_refs"]
        assert candidate["raw_keyword_semantic_oracle_used"] is False


def test_candidate_extraction_blocks_raw_keyword_semantic_oracle() -> None:
    from app.memory.application.runtime_lab_candidate_extraction import (
        extract_candidate_from_edd_case,
    )
    from app.memory.application.runtime_lab_memory_edd import (
        load_runtime_lab_memory_edd_suite,
    )

    case = dict(load_runtime_lab_memory_edd_suite()["cases"][0])
    case["oracle"] = {
        "semantic_oracle_source": "raw_keyword_rules",
        "raw_keyword_route_allowed": True,
    }

    result = extract_candidate_from_edd_case(case)

    assert result["outcome"] == "rejected"
    assert result["rejection_reason"] == "raw_keyword_semantic_oracle_blocked"


def test_candidate_extraction_requires_trace_field_not_user_text() -> None:
    from app.memory.application.runtime_lab_candidate_extraction import (
        extract_candidate_from_edd_case,
    )
    from app.memory.application.runtime_lab_memory_edd import (
        load_runtime_lab_memory_edd_suite,
    )

    case = dict(load_runtime_lab_memory_edd_suite()["cases"][0])
    case["user_message"] = "preference-like text is not enough"
    case["trace_fields"] = {"source_refs": ["message:no-manager-field"]}

    result = extract_candidate_from_edd_case(case)

    assert result["outcome"] == "rejected"
    assert result["rejection_reason"] == "missing_manager_decision_field"


def test_candidate_extraction_from_ingress_event_builds_review_candidate_only() -> None:
    from app.memory.application.runtime_lab_candidate_extraction import (
        build_candidate_extraction_artifact_from_ingress_events,
    )
    from app.memory.application.runtime_lab_trace_ingress import (
        build_memory_ingress_event_from_manager_trace,
    )

    event = build_memory_ingress_event_from_manager_trace(_candidate_trace())
    artifact = build_candidate_extraction_artifact_from_ingress_events([event])

    assert artifact["status"] == "pass"
    assert artifact["runtime_connected"] is True
    assert artifact["candidate_count"] == 1
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["manager_context_packet_changed"] is False
    candidate = artifact["candidates"][0]
    assert candidate["candidate_type"] == "preference"
    assert candidate["runtime_effect_allowed"] is False
    assert candidate["promotion_allowed_now"] is False
    assert candidate["source_object_refs"] == ["message:dogfood-preference-001"]


def test_candidate_extraction_runner_writes_dogfood_replay_artifact(
    tmp_path: Path,
) -> None:
    trace_path = tmp_path / "trace.json"
    output_path = tmp_path / "candidate_extraction.json"
    trace_path.write_text(json.dumps(_candidate_trace()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_runtime_lab_memory_candidate_extraction.py"),
            "--trace-json",
            str(trace_path),
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["artifact_type"] == "runtime_lab_memory_candidate_extraction"
    assert artifact["live_dogfood_replay"] is False
    assert artifact["candidate_count"] == 1
    assert artifact["runtime_effect_allowed"] is False
