from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_only_pack(**overrides: object) -> dict[str, object]:
    pack: dict[str, object] = {
        "artifact_type": "runtime_lab_memory_read_only_runtime_lab_pack",
        "status": "pass",
        "capability": "long_term_memory",
        "current_stage": "shadow",
        "target_stage": "read_only_runtime",
        "source_artifacts": [
            "runtime_lab_memory_edd_suite",
            "runtime_lab_memory_candidate_extraction",
            "runtime_lab_memory_lifecycle_decision",
            "shadow_memory_context_pack",
            "runtime_lab_manager_memory_injection_comparison",
            "runtime_lab_memory_consumer_summary_projection",
        ],
        "reviewed_memory_pack_loaded": True,
        "stage_evidence": {
            "scope_isolation_check": True,
            "paired_baseline_comparison": True,
            "omission_trace_present": True,
            "latency_budget_observed": True,
            "no_commit_fallback": True,
        },
        "paired_baseline_evidence": {
            "baseline_run_type": "baseline_trace_replay",
            "memory_context_run_type": "memory_context_trace_replay",
            "final_response_changed": False,
            "shadow_memory_context_pack_used": True,
            "tool_calls_blocked": True,
            "mutation_attempts_blocked": True,
        },
        "blockers": [],
        "manual_promotion_review_allowed": True,
        "automatic_stage_promotion_allowed": False,
        "runtime_connected": True,
        "lab_isolated": True,
        "mainline_runtime_connected": False,
        "manager_context_packet_changed": False,
        "manager_context_injected": False,
        "durable_product_memory_written": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
        "mutation_changed": False,
        "runtime_effect_allowed": False,
        "recommendation_served": False,
        "rescue_proposal_committed": False,
        "proactive_sent": False,
        "scheduler_enabled": False,
    }
    pack.update(overrides)
    return pack


def _review_decision(**overrides: object) -> dict[str, object]:
    review: dict[str, object] = {
        "artifact_type": "runtime_lab_memory_stage_promotion_review_decision",
        "decision": "approved",
        "reviewer_id": "fixture-human-reviewer",
        "reviewed_at": "2026-05-09T21:30:00+08:00",
        "capability": "long_term_memory",
        "current_stage": "shadow",
        "target_stage": "read_only_runtime",
        "reviewed_read_only_runtime_lab_pack": True,
        "scope_keys": {
            "user_id": "user-a",
            "workspace_id": "workspace-a",
            "project_id": "advanced-memory-runtime-lab",
            "surface": "manager_runtime_lab",
            "run_id": "report-run-001",
        },
        "mainline_runtime_activation_approved": False,
        "manager_context_packet_change_approved": False,
        "durable_memory_write_approved": False,
        "downstream_activation_approved": False,
    }
    review.update(overrides)
    return review


def test_stage_promotion_decision_records_manual_ltm_read_only_runtime_approval() -> None:
    from app.memory.application.runtime_lab_stage_promotion import (
        build_runtime_lab_memory_stage_promotion_decision,
    )

    decision = build_runtime_lab_memory_stage_promotion_decision(
        read_only_runtime_lab_pack=_read_only_pack(),
        human_review_decision=_review_decision(),
    )

    assert decision["artifact_type"] == "runtime_lab_memory_stage_promotion_decision"
    assert decision["status"] == "approved"
    assert decision["capability"] == "long_term_memory"
    assert decision["current_stage"] == "shadow"
    assert decision["target_stage"] == "read_only_runtime"
    assert decision["activation_stage_after_decision"] == "read_only_runtime"
    assert decision["stage_change_recorded"] is True
    assert decision["manual_promotion_approved"] is True
    assert decision["human_review_required"] is True
    assert decision["automatic_stage_promotion_allowed"] is False
    assert decision["scope_keys"]["project_id"] == "advanced-memory-runtime-lab"
    assert decision["source_read_only_runtime_pack_type"] == (
        "runtime_lab_memory_read_only_runtime_lab_pack"
    )
    assert decision["source_artifacts"] == _read_only_pack()["source_artifacts"]
    assert decision["mainline_runtime_connected"] is False
    assert decision["manager_context_packet_changed"] is False
    assert decision["durable_product_memory_written"] is False
    assert decision["user_facing_behavior_changed"] is False
    assert decision["canonical_mutation_changed"] is False
    assert decision["recommendation_served"] is False
    assert decision["rescue_proposal_committed"] is False
    assert decision["proactive_sent"] is False
    assert "not_recommendation_read_only_runtime_promotion" in decision["non_claims"]


def test_stage_promotion_decision_stays_pending_without_human_review() -> None:
    from app.memory.application.runtime_lab_stage_promotion import (
        build_runtime_lab_memory_stage_promotion_decision,
    )

    decision = build_runtime_lab_memory_stage_promotion_decision(
        read_only_runtime_lab_pack=_read_only_pack(),
        human_review_decision=None,
    )

    assert decision["status"] == "pending_review"
    assert decision["blockers"] == ["human_review_decision_missing"]
    assert decision["activation_stage_after_decision"] == "shadow"
    assert decision["stage_change_recorded"] is False
    assert decision["manual_promotion_approved"] is False
    assert decision["automatic_stage_promotion_allowed"] is False


def test_stage_promotion_decision_blocks_pack_or_no_go_drift() -> None:
    from app.memory.application.runtime_lab_stage_promotion import (
        build_runtime_lab_memory_stage_promotion_decision,
    )

    decision = build_runtime_lab_memory_stage_promotion_decision(
        read_only_runtime_lab_pack=_read_only_pack(
            recommendation_served=True,
            stage_evidence={"scope_isolation_check": False},
        ),
        human_review_decision=_review_decision(),
    )

    assert decision["status"] == "blocked"
    assert "read_only_runtime_lab_pack.recommendation_served" in decision["blockers"]
    assert "read_only_runtime_lab_pack.missing_paired_baseline_comparison" in decision[
        "blockers"
    ]
    assert decision["activation_stage_after_decision"] == "shadow"
    assert decision["stage_change_recorded"] is False


def test_stage_promotion_decision_rejects_review_overclaim() -> None:
    from app.memory.application.runtime_lab_stage_promotion import (
        build_runtime_lab_memory_stage_promotion_decision,
    )

    decision = build_runtime_lab_memory_stage_promotion_decision(
        read_only_runtime_lab_pack=_read_only_pack(),
        human_review_decision=_review_decision(
            mainline_runtime_activation_approved=True,
            scope_keys={"user_id": "user-a"},
        ),
    )

    assert decision["status"] == "blocked"
    assert "human_review_decision.mainline_runtime_activation_approved" in decision[
        "blockers"
    ]
    assert "human_review_decision.scope_keys_missing:workspace_id" in decision["blockers"]
    assert decision["stage_change_recorded"] is False


def test_stage_promotion_decision_runner_reads_quality_report_pack(
    tmp_path: Path,
) -> None:
    quality_report_path = tmp_path / "quality_report.json"
    review_decision_path = tmp_path / "review_decision.json"
    output_path = tmp_path / "stage_promotion_decision.json"
    quality_report_path.write_text(
        json.dumps(
            {
                "artifact_type": "runtime_lab_memory_shadow_quality_report",
                "status": "pass",
                "read_only_runtime_lab_pack": _read_only_pack(),
            }
        ),
        encoding="utf-8",
    )
    review_decision_path.write_text(
        json.dumps(_review_decision()),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_runtime_lab_memory_stage_promotion_decision.py"),
            "--quality-report-json",
            str(quality_report_path),
            "--review-decision-json",
            str(review_decision_path),
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
    assert artifact["status"] == "approved"
    assert artifact["activation_stage_after_decision"] == "read_only_runtime"
    assert artifact["mainline_runtime_connected"] is False
