from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _memory_stage_decision(**overrides: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "artifact_type": "runtime_lab_memory_stage_promotion_decision",
        "status": "approved",
        "capability": "long_term_memory",
        "current_stage": "shadow",
        "target_stage": "read_only_runtime",
        "activation_stage_after_decision": "read_only_runtime",
        "stage_change_recorded": True,
        "manual_promotion_approved": True,
        "human_review_required": True,
        "automatic_stage_promotion_allowed": False,
        "fixture_kind": "synthetic_merge_safe_contract_fixture",
        "scope_keys": {
            "user_id": "user-a",
            "workspace_id": "workspace-a",
            "project_id": "advanced-memory-runtime-lab",
            "surface": "manager_runtime_lab",
            "run_id": "report-run-001",
        },
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
        "no_go_flags": {"recommendation_served": False},
    }
    decision.update(overrides)
    return decision


def _recommendation_report(**overrides: object) -> dict[str, object]:
    report: dict[str, object] = {
        "artifact_type": "recommendation_shadow_summary_consumer_quality_report",
        "status": "pass",
        "blockers": [],
        "owner": "app/recommendation",
        "consumer": "future recommendation/proactive activation slices",
        "source_memory_artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "source_recommendation_artifact_type": "recommendation_three_node_shadow_artifact",
        "memory_summary_projection_used": True,
        "canonical_recommendation_graph": "three_node",
        "three_node_lab_bridge_used": True,
        "five_node_lab_bridge_used": False,
        "candidate_count": 1,
        "candidate_evaluations": [{"candidate_id": "golden-1", "quality_gate_passed": True}],
        "runtime_connected": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "live_search_used": False,
        "ranking_llm_invoked": False,
        "intake_handoff_created": False,
        "mutation_changed": False,
        "durable_memory_written": False,
        "manager_context_packet_changed": False,
        "manager_context_injected": False,
    }
    report.update(overrides)
    return report


def test_preflight_augments_existing_report_without_serving_recommendation() -> None:
    from app.recommendation.application.read_only_runtime_preflight import (
        build_recommendation_read_only_runtime_preflight_report,
    )

    report = build_recommendation_read_only_runtime_preflight_report(
        memory_stage_promotion_decision=_memory_stage_decision(),
        recommendation_summary_report=_recommendation_report(),
    )

    preflight = report["read_only_runtime_preflight"]
    assert report["artifact_type"] == "recommendation_shadow_summary_consumer_quality_report"
    assert report["status"] == "pass"
    assert preflight["status"] == "pass"
    assert preflight["capability"] == "recommendation"
    assert preflight["current_stage"] == "shadow"
    assert preflight["target_stage"] == "read_only_runtime"
    assert preflight["dependency_satisfied"] == "long_term_memory.read_only_runtime"
    assert preflight["source_stage_promotion_fixture_kind"] == (
        "synthetic_merge_safe_contract_fixture"
    )
    assert preflight["manual_promotion_review_allowed"] is True
    assert preflight["automatic_stage_promotion_allowed"] is False
    assert preflight["recommendation_read_only_runtime_promoted"] is False
    assert report["recommendation_served"] is False
    assert report["live_search_used"] is False
    assert report["ranking_llm_invoked"] is False
    assert report["intake_handoff_created"] is False
    assert report["manager_context_packet_changed"] is False


def test_preflight_blocks_missing_or_pending_memory_stage_promotion() -> None:
    from app.recommendation.application.read_only_runtime_preflight import (
        build_recommendation_read_only_runtime_preflight_report,
    )

    report = build_recommendation_read_only_runtime_preflight_report(
        memory_stage_promotion_decision=_memory_stage_decision(
            status="pending_review",
            activation_stage_after_decision="shadow",
            manual_promotion_approved=False,
        ),
        recommendation_summary_report=_recommendation_report(),
    )

    assert report["status"] == "blocked"
    assert "read_only_runtime_preflight.memory_stage_promotion.status_not_approved" in report[
        "blockers"
    ]
    assert "memory_stage_promotion.activation_stage_not_read_only_runtime" in report[
        "read_only_runtime_preflight"
    ]["blockers"]
    assert report["read_only_runtime_preflight"]["manual_promotion_review_allowed"] is False


def test_preflight_blocks_stage_decision_or_recommendation_overclaim() -> None:
    from app.recommendation.application.read_only_runtime_preflight import (
        build_recommendation_read_only_runtime_preflight_report,
    )

    report = build_recommendation_read_only_runtime_preflight_report(
        memory_stage_promotion_decision=_memory_stage_decision(
            manager_context_packet_changed=True,
            no_go_flags={"recommendation_served": True},
        ),
        recommendation_summary_report=_recommendation_report(
            recommendation_served=True,
            live_search_used=True,
        ),
    )

    assert report["status"] == "blocked"
    blockers = report["read_only_runtime_preflight"]["blockers"]
    assert "memory_stage_promotion.manager_context_packet_changed" in blockers
    assert "memory_stage_promotion.no_go_flag_true:recommendation_served" in blockers
    assert "recommendation_summary_report.recommendation_served" in blockers
    assert "recommendation_summary_report.live_search_used" in blockers
    assert report["recommendation_served"] is False


def test_preflight_runner_requires_real_artifact_inputs(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory_stage_decision.json"
    recommendation_path = tmp_path / "recommendation_report.json"
    output_path = tmp_path / "recommendation_preflight.json"
    memory_path.write_text(json.dumps(_memory_stage_decision()), encoding="utf-8")
    recommendation_path.write_text(json.dumps(_recommendation_report()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_recommendation_read_only_runtime_preflight.py"),
            "--memory-stage-promotion-decision-json",
            str(memory_path),
            "--recommendation-summary-report-json",
            str(recommendation_path),
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
    assert artifact["artifact_type"] == "recommendation_shadow_summary_consumer_quality_report"
    assert artifact["read_only_runtime_preflight"]["status"] == "pass"
    assert artifact["read_only_runtime_preflight"]["real_artifact_input_required"] is True
