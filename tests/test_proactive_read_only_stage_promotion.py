from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _preflight(**overrides: object) -> dict[str, object]:
    preflight: dict[str, object] = {
        "artifact_type": "proactive_read_only_runtime_preflight_report",
        "status": "pass",
        "blockers": [],
        "capability": "proactive",
        "current_stage": "shadow",
        "target_stage": "read_only_runtime",
        "dependency_satisfied": [
            "recommendation.read_only_runtime",
            "rescue.read_only_runtime",
        ],
        "manual_promotion_review_allowed": True,
        "automatic_stage_promotion_allowed": False,
        "proactive_read_only_runtime_promoted": False,
        "preflight_only": True,
        "real_artifact_input_required": True,
        "runtime_effect_allowed": False,
        "real_runtime_effect": False,
        "proactive_sent": False,
        "scheduler_enabled": False,
        "live_delivery_allowed": False,
        "scheduler_activation_allowed": False,
        "manager_context_packet_changed": False,
        "manager_context_injected": False,
        "recommendation_served": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "meal_thread_mutated": False,
        "durable_memory_written": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
        "product_readiness_claimed": False,
        "no_go_flags": {"proactive_sent": False},
    }
    preflight.update(overrides)
    return preflight


def _review(**overrides: object) -> dict[str, object]:
    review: dict[str, object] = {
        "artifact_type": "proactive_read_only_runtime_stage_review_decision",
        "decision": "approved",
        "reviewer_id": "fixture-human-reviewer",
        "reviewed_at": "2026-05-10T07:10:00+08:00",
        "capability": "proactive",
        "current_stage": "shadow",
        "target_stage": "read_only_runtime",
        "reviewed_read_only_runtime_preflight": True,
        "fixture_kind": "synthetic_merge_safe_contract_fixture",
        "scope_keys": {
            "user_id": "user-a",
            "workspace_id": "workspace-a",
            "project_id": "advanced-proactive-runtime-lab",
            "surface": "proactive_runtime_lab",
            "run_id": "proactive-stage-001",
        },
        "mainline_runtime_activation_approved": False,
        "scheduler_activation_approved": False,
        "live_delivery_approved": False,
        "notification_delivery_approved": False,
        "route_or_api_activation_approved": False,
        "user_facing_behavior_approved": False,
        "manager_context_packet_change_approved": False,
        "durable_memory_write_approved": False,
        "durable_snooze_write_approved": False,
        "live_llm_invocation_approved": False,
        "mutation_approved": False,
    }
    review.update(overrides)
    return review


def test_proactive_stage_decision_records_manual_read_only_runtime_approval() -> None:
    from app.runtime.application.proactive_read_only_stage_promotion import (
        build_proactive_read_only_stage_promotion_decision,
    )

    decision = build_proactive_read_only_stage_promotion_decision(
        proactive_preflight_report=_preflight(),
        human_review_decision=_review(),
    )

    assert decision["artifact_type"] == "proactive_read_only_runtime_stage_decision"
    assert decision["status"] == "approved"
    assert decision["capability"] == "proactive"
    assert decision["activation_stage_after_decision"] == "read_only_runtime"
    assert decision["stage_change_recorded"] is True
    assert decision["manual_promotion_approved"] is True
    assert decision["proactive_read_only_runtime_promoted"] is True
    assert decision["scheduler_activation_allowed"] is False
    assert decision["live_delivery_allowed"] is False
    assert decision["proactive_sent"] is False
    assert decision["manager_context_packet_changed"] is False
    assert decision["source_review_fixture_kind"] == (
        "synthetic_merge_safe_contract_fixture"
    )
    assert "not_scheduler_activation" in decision["non_claims"]


def test_proactive_stage_decision_stays_pending_without_human_review() -> None:
    from app.runtime.application.proactive_read_only_stage_promotion import (
        build_proactive_read_only_stage_promotion_decision,
    )

    decision = build_proactive_read_only_stage_promotion_decision(
        proactive_preflight_report=_preflight(),
        human_review_decision=None,
    )

    assert decision["status"] == "pending_review"
    assert decision["blockers"] == ["human_review_decision_missing"]
    assert decision["activation_stage_after_decision"] == "shadow"
    assert decision["stage_change_recorded"] is False


def test_proactive_stage_decision_blocks_preflight_or_no_go_drift() -> None:
    from app.runtime.application.proactive_read_only_stage_promotion import (
        build_proactive_read_only_stage_promotion_decision,
    )

    decision = build_proactive_read_only_stage_promotion_decision(
        proactive_preflight_report=_preflight(
            status="blocked",
            blockers=["fixture_blocker"],
            scheduler_enabled=True,
        ),
        human_review_decision=_review(),
    )

    assert decision["status"] == "blocked"
    assert "proactive_preflight.status_not_pass" in decision["blockers"]
    assert "proactive_preflight.fixture_blocker" in decision["blockers"]
    assert "proactive_preflight.scheduler_enabled" in decision["blockers"]
    assert decision["activation_stage_after_decision"] == "shadow"
    assert decision["scheduler_enabled"] is False


def test_proactive_stage_decision_rejects_review_overclaim() -> None:
    from app.runtime.application.proactive_read_only_stage_promotion import (
        build_proactive_read_only_stage_promotion_decision,
    )

    decision = build_proactive_read_only_stage_promotion_decision(
        proactive_preflight_report=_preflight(),
        human_review_decision=_review(
            live_delivery_approved=True,
            scheduler_activation_approved=True,
            scope_keys={"user_id": "user-a"},
        ),
    )

    assert decision["status"] == "blocked"
    assert "human_review_decision.live_delivery_approved" in decision["blockers"]
    assert "human_review_decision.scheduler_activation_approved" in decision["blockers"]
    assert "human_review_decision.scope_keys_missing:workspace_id" in decision[
        "blockers"
    ]
    assert decision["stage_change_recorded"] is False


def test_proactive_stage_decision_runner_requires_artifact_inputs(
    tmp_path: Path,
) -> None:
    preflight_path = tmp_path / "proactive_preflight.json"
    review_path = tmp_path / "review.json"
    output_path = tmp_path / "decision.json"
    preflight_path.write_text(json.dumps(_preflight()), encoding="utf-8")
    review_path.write_text(json.dumps(_review()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_proactive_read_only_stage_promotion.py"),
            "--proactive-preflight-json",
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
    assert artifact["artifact_type"] == "proactive_read_only_runtime_stage_decision"
    assert artifact["status"] == "approved"
    assert artifact["real_artifact_input_required"] is True
