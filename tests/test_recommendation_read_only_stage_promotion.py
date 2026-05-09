from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _preflight(**overrides: object) -> dict[str, object]:
    preflight: dict[str, object] = {
        "artifact_type": "recommendation_shadow_summary_consumer_quality_report",
        "status": "pass",
        "blockers": [],
        "read_only_runtime_preflight": {
            "artifact_type": "recommendation_read_only_runtime_preflight",
            "status": "pass",
            "blockers": [],
            "capability": "recommendation",
            "current_stage": "shadow",
            "target_stage": "read_only_runtime",
            "dependency_satisfied": "long_term_memory.read_only_runtime",
            "manual_promotion_review_allowed": True,
            "automatic_stage_promotion_allowed": False,
            "recommendation_read_only_runtime_promoted": False,
            "preflight_only": True,
            "real_artifact_input_required": True,
        },
        "recommendation_served": False,
        "live_search_used": False,
        "ranking_llm_invoked": False,
        "intake_handoff_created": False,
        "manager_context_packet_changed": False,
        "manager_context_injected": False,
        "durable_memory_written": False,
        "mutation_changed": False,
        "proactive_sent": False,
    }
    preflight.update(overrides)
    return preflight


def _review(**overrides: object) -> dict[str, object]:
    review: dict[str, object] = {
        "artifact_type": "recommendation_read_only_runtime_stage_review_decision",
        "decision": "approved",
        "reviewer_id": "fixture-human-reviewer",
        "reviewed_at": "2026-05-09T22:00:00+08:00",
        "capability": "recommendation",
        "current_stage": "shadow",
        "target_stage": "read_only_runtime",
        "reviewed_read_only_runtime_preflight": True,
        "fixture_kind": "synthetic_merge_safe_contract_fixture",
        "scope_keys": {
            "user_id": "user-a",
            "workspace_id": "workspace-a",
            "project_id": "advanced-recommendation-runtime-lab",
            "surface": "recommendation_runtime_lab",
            "run_id": "recommendation-stage-001",
        },
        "mainline_runtime_activation_approved": False,
        "recommendation_serving_approved": False,
        "live_search_approved": False,
        "ranking_llm_approved": False,
        "intake_handoff_approved": False,
        "manager_context_packet_change_approved": False,
        "scheduler_delivery_approved": False,
        "mutation_approved": False,
    }
    review.update(overrides)
    return review


def test_recommendation_stage_decision_records_manual_read_only_runtime_approval() -> None:
    from app.recommendation.application.read_only_stage_promotion import (
        build_recommendation_read_only_stage_promotion_decision,
    )

    decision = build_recommendation_read_only_stage_promotion_decision(
        recommendation_preflight_report=_preflight(),
        human_review_decision=_review(),
    )

    assert decision["artifact_type"] == "recommendation_read_only_runtime_stage_decision"
    assert decision["status"] == "approved"
    assert decision["capability"] == "recommendation"
    assert decision["current_stage"] == "shadow"
    assert decision["target_stage"] == "read_only_runtime"
    assert decision["activation_stage_after_decision"] == "read_only_runtime"
    assert decision["stage_change_recorded"] is True
    assert decision["manual_promotion_approved"] is True
    assert decision["human_review_required"] is True
    assert decision["automatic_stage_promotion_allowed"] is False
    assert decision["source_preflight_artifact_type"] == (
        "recommendation_read_only_runtime_preflight"
    )
    assert decision["source_review_fixture_kind"] == (
        "synthetic_merge_safe_contract_fixture"
    )
    assert decision["recommendation_served"] is False
    assert decision["live_search_used"] is False
    assert decision["ranking_llm_invoked"] is False
    assert decision["intake_handoff_created"] is False
    assert decision["manager_context_packet_changed"] is False
    assert "not_proactive_read_only_runtime_promotion" in decision["non_claims"]


def test_recommendation_stage_decision_stays_pending_without_human_review() -> None:
    from app.recommendation.application.read_only_stage_promotion import (
        build_recommendation_read_only_stage_promotion_decision,
    )

    decision = build_recommendation_read_only_stage_promotion_decision(
        recommendation_preflight_report=_preflight(),
        human_review_decision=None,
    )

    assert decision["status"] == "pending_review"
    assert decision["blockers"] == ["human_review_decision_missing"]
    assert decision["activation_stage_after_decision"] == "shadow"
    assert decision["stage_change_recorded"] is False


def test_recommendation_stage_decision_blocks_preflight_or_no_go_drift() -> None:
    from app.recommendation.application.read_only_stage_promotion import (
        build_recommendation_read_only_stage_promotion_decision,
    )

    preflight = _preflight(recommendation_served=True)
    preflight["read_only_runtime_preflight"]["status"] = "blocked"  # type: ignore[index]
    preflight["read_only_runtime_preflight"]["blockers"] = ["fixture_blocker"]  # type: ignore[index]

    decision = build_recommendation_read_only_stage_promotion_decision(
        recommendation_preflight_report=preflight,
        human_review_decision=_review(),
    )

    assert decision["status"] == "blocked"
    assert "recommendation_preflight.status_not_pass" in decision["blockers"]
    assert "recommendation_preflight.fixture_blocker" in decision["blockers"]
    assert "recommendation_preflight.report.recommendation_served" in decision["blockers"]
    assert decision["activation_stage_after_decision"] == "shadow"
    assert decision["recommendation_served"] is False


def test_recommendation_stage_decision_rejects_review_overclaim() -> None:
    from app.recommendation.application.read_only_stage_promotion import (
        build_recommendation_read_only_stage_promotion_decision,
    )

    decision = build_recommendation_read_only_stage_promotion_decision(
        recommendation_preflight_report=_preflight(),
        human_review_decision=_review(
            recommendation_serving_approved=True,
            scope_keys={"user_id": "user-a"},
        ),
    )

    assert decision["status"] == "blocked"
    assert "human_review_decision.recommendation_serving_approved" in decision[
        "blockers"
    ]
    assert "human_review_decision.scope_keys_missing:workspace_id" in decision["blockers"]
    assert decision["stage_change_recorded"] is False


def test_recommendation_stage_decision_runner_requires_artifact_inputs(
    tmp_path: Path,
) -> None:
    preflight_path = tmp_path / "recommendation_preflight.json"
    review_path = tmp_path / "review.json"
    output_path = tmp_path / "decision.json"
    preflight_path.write_text(json.dumps(_preflight()), encoding="utf-8")
    review_path.write_text(json.dumps(_review()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_recommendation_read_only_stage_promotion.py"),
            "--recommendation-preflight-json",
            str(preflight_path),
            "--review-decision-json",
            str(review_path),
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
    assert artifact["artifact_type"] == "recommendation_read_only_runtime_stage_decision"
    assert artifact["status"] == "approved"
    assert artifact["real_artifact_input_required"] is True
