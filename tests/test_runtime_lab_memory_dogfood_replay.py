from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _trace(request_id: str = "rt-lab-dogfood-001") -> dict:
    return {
        "request_id": request_id,
        "trace_meta": {
            "request_id": request_id,
            "user_id": "user-a",
            "bundle": "intake_execution",
            "local_date": "2026-05-09",
        },
        "memory_lab_scope": {
            "workspace_id": "workspace-a",
            "project_id": "advanced-memory-runtime-lab",
            "surface": "manager_runtime_lab",
            "run_id": f"{request_id}-run",
        },
        "request": {
            "user_id": "user-a",
            "text": "private dogfood wording should not become the oracle",
            "allow_search": False,
        },
        "manager_final_decision": {
            "intent": "log_meal",
            "workflow_effect": "commit_meal_log",
        },
        "memory_lab_candidate_signal": {
            "candidate_type": "preference",
            "manager_decision_field": "memory_candidate_requested",
            "source_refs": [f"message:{request_id}"],
            "review_status": "pending",
            "promotion_allowed_now": False,
            "human_review_required": True,
            "reason_codes": ["explicit_user_preference"],
        },
    }


def _reviewed_record(
    *,
    request_id: str = "rt-lab-dogfood-001",
    split: str = "holdout",
) -> dict:
    return {
        "trace": _trace(request_id),
        "review": {
            "reviewer_id": "fixture-human-reviewer",
            "case_type": "explicit_preference",
            "split": split,
            "expected_outcome": "candidate",
            "expected_candidate_type": "preference",
            "semantic_oracle_source": "product_rule_and_trace_fields",
            "raw_keyword_route_allowed": False,
            "source_ref_confirmation": True,
        },
    }


def test_dogfood_replay_builds_reviewed_edd_expansion_without_runtime_effects() -> None:
    from app.memory.application.runtime_lab_dogfood_replay import (
        build_memory_dogfood_replay_review_artifact,
    )

    artifact = build_memory_dogfood_replay_review_artifact(
        [
            _reviewed_record(request_id="rt-lab-dogfood-001", split="fixture"),
            _reviewed_record(request_id="rt-lab-dogfood-002", split="holdout"),
        ]
    )

    assert artifact["artifact_type"] == "runtime_lab_memory_dogfood_replay_review"
    assert artifact["status"] == "pass"
    assert artifact["owner"] == "app/memory"
    assert artifact["consumer"] == "runtime_lab_memory_quality_report"
    assert artifact["retirement_trigger"] == "approved_memory_runtime_activation_plan"
    assert artifact["proposed_split_counts"] == {"fixture": 1, "holdout": 1}
    assert artifact["reviewed_case_count"] == 2
    assert artifact["runtime_connected"] is True
    assert artifact["lab_isolated"] is True
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["canonical_mutation_changed"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["shadow_memory_context_pack_used"] is False

    case = artifact["reviewed_case_proposals"][0]
    assert case["source"] == "dogfood_replay"
    assert case["split"] == "fixture"
    assert case["oracle"] == {
        "semantic_oracle_source": "product_rule_and_trace_fields",
        "raw_keyword_route_allowed": False,
    }
    assert case["expected_runtime_effects"] == {
        "runtime_connected": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }
    assert "user_message" not in case
    assert case["expected_candidate"]["promotion_allowed_now"] is False
    assert case["expected_candidate"]["human_review_required"] is True


def test_dogfood_replay_blocks_missing_reviewer_and_raw_keyword_oracle() -> None:
    from app.memory.application.runtime_lab_dogfood_replay import (
        build_memory_dogfood_replay_review_artifact,
    )

    missing_reviewer = _reviewed_record(request_id="rt-lab-dogfood-no-reviewer")
    missing_reviewer["review"].pop("reviewer_id")
    keyword_oracle = _reviewed_record(request_id="rt-lab-dogfood-keyword")
    keyword_oracle["review"]["semantic_oracle_source"] = "raw_keyword_rules"
    keyword_oracle["review"]["raw_keyword_route_allowed"] = True

    artifact = build_memory_dogfood_replay_review_artifact(
        [missing_reviewer, keyword_oracle]
    )

    assert artifact["status"] == "blocked"
    assert artifact["reviewed_case_count"] == 0
    assert artifact["proposed_split_counts"] == {}
    assert artifact["durable_product_memory_written"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["blockers"] == [
        "rt-lab-dogfood-no-reviewer.missing_review_reviewer_id",
        "rt-lab-dogfood-keyword.raw_keyword_semantic_oracle_blocked",
    ]


def test_dogfood_replay_blocks_candidate_without_source_refs() -> None:
    from app.memory.application.runtime_lab_dogfood_replay import (
        build_memory_dogfood_replay_review_artifact,
    )

    missing_refs = _reviewed_record(request_id="rt-lab-dogfood-no-source")
    missing_refs["trace"]["memory_lab_candidate_signal"]["source_refs"] = []

    artifact = build_memory_dogfood_replay_review_artifact([missing_refs])

    assert artifact["status"] == "blocked"
    assert artifact["reviewed_case_count"] == 0
    assert artifact["blockers"] == [
        "rt-lab-dogfood-no-source.missing_candidate_source_refs"
    ]


def test_dogfood_replay_runner_writes_non_claim_artifact(tmp_path: Path) -> None:
    input_path = tmp_path / "reviewed_traces.json"
    output_path = tmp_path / "dogfood_replay_review.json"
    input_path.write_text(
        json.dumps([_reviewed_record()], ensure_ascii=False),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_runtime_lab_memory_dogfood_replay.py"),
            "--reviewed-traces-json",
            str(input_path),
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
    assert artifact["artifact_type"] == "runtime_lab_memory_dogfood_replay_review"
    assert artifact["status"] == "pass"
    assert artifact["live_evidence_required_for_merge"] is False
    assert artifact["non_claims"] == [
        "not_product_activation_evidence",
        "not_private_self_use_approval",
        "not_mainline_manager_memory_context_injection",
        "not_durable_product_memory",
    ]
