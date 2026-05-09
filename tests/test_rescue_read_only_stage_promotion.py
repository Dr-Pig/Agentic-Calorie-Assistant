from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _preflight(**overrides: object) -> dict[str, object]:
    preflight: dict[str, object] = {
        "artifact_type": "rescue_read_only_runtime_preflight_report",
        "status": "pass",
        "blockers": [],
        "capability": "rescue",
        "current_stage": "shadow",
        "target_stage": "read_only_runtime",
        "dependency_satisfied": "long_term_memory.read_only_runtime",
        "source_stage_promotion_fixture_kind": "synthetic_merge_safe_contract_fixture",
        "manual_promotion_review_allowed": True,
        "automatic_stage_promotion_allowed": False,
        "rescue_read_only_runtime_promoted": False,
        "preflight_only": True,
        "real_artifact_input_required": True,
        "runtime_effect_allowed": False,
        "rescue_proposal_committed": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "ledger_entry_created": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "meal_thread_mutated": False,
        "durable_memory_written": False,
        "manager_context_packet_changed": False,
        "manager_context_injected": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
        "proactive_sent": False,
        "recommendation_served": False,
        "scheduler_enabled": False,
    }
    preflight.update(overrides)
    return preflight


def _review(**overrides: object) -> dict[str, object]:
    review: dict[str, object] = {
        "artifact_type": "rescue_read_only_runtime_stage_review_decision",
        "decision": "approved",
        "reviewer_id": "fixture-human-reviewer",
        "reviewed_at": "2026-05-10T06:20:00+08:00",
        "capability": "rescue",
        "current_stage": "shadow",
        "target_stage": "read_only_runtime",
        "reviewed_read_only_runtime_preflight": True,
        "fixture_kind": "synthetic_merge_safe_contract_fixture",
        "scope_keys": {
            "user_id": "user-a",
            "workspace_id": "workspace-a",
            "project_id": "advanced-rescue-runtime-lab",
            "surface": "rescue_runtime_lab",
            "run_id": "rescue-stage-001",
        },
        "mainline_runtime_activation_approved": False,
        "rescue_serving_approved": False,
        "rescue_proposal_approved": False,
        "rescue_commit_approved": False,
        "scheduler_delivery_approved": False,
        "manager_context_packet_change_approved": False,
        "route_or_api_activation_approved": False,
        "downstream_activation_approved": False,
        "mutation_approved": False,
    }
    review.update(overrides)
    return review


def test_rescue_stage_decision_records_manual_read_only_runtime_approval() -> None:
    from app.rescue.application.read_only_stage_promotion import (
        build_rescue_read_only_stage_promotion_decision,
    )

    decision = build_rescue_read_only_stage_promotion_decision(
        rescue_preflight_report=_preflight(),
        human_review_decision=_review(),
    )

    assert decision["artifact_type"] == "rescue_read_only_runtime_stage_decision"
    assert decision["status"] == "approved"
    assert decision["capability"] == "rescue"
    assert decision["activation_stage_after_decision"] == "read_only_runtime"
    assert decision["stage_change_recorded"] is True
    assert decision["manual_promotion_approved"] is True
    assert decision["rescue_read_only_runtime_promoted"] is True
    assert decision["human_review_required"] is True
    assert decision["automatic_stage_promotion_allowed"] is False
    assert decision["source_preflight_artifact_type"] == (
        "rescue_read_only_runtime_preflight_report"
    )
    assert decision["source_review_fixture_kind"] == (
        "synthetic_merge_safe_contract_fixture"
    )
    assert decision["rescue_proposal_committed"] is False
    assert decision["ledger_entry_created"] is False
    assert decision["manager_context_packet_changed"] is False
    assert "not_proactive_read_only_runtime_promotion" in decision["non_claims"]


def test_rescue_stage_decision_stays_pending_without_human_review() -> None:
    from app.rescue.application.read_only_stage_promotion import (
        build_rescue_read_only_stage_promotion_decision,
    )

    decision = build_rescue_read_only_stage_promotion_decision(
        rescue_preflight_report=_preflight(),
        human_review_decision=None,
    )

    assert decision["status"] == "pending_review"
    assert decision["blockers"] == ["human_review_decision_missing"]
    assert decision["activation_stage_after_decision"] == "shadow"
    assert decision["stage_change_recorded"] is False


def test_rescue_stage_decision_blocks_preflight_or_no_go_drift() -> None:
    from app.rescue.application.read_only_stage_promotion import (
        build_rescue_read_only_stage_promotion_decision,
    )

    decision = build_rescue_read_only_stage_promotion_decision(
        rescue_preflight_report=_preflight(
            status="blocked",
            blockers=["fixture_blocker"],
            rescue_proposal_committed=True,
        ),
        human_review_decision=_review(),
    )

    assert decision["status"] == "blocked"
    assert "rescue_preflight.status_not_pass" in decision["blockers"]
    assert "rescue_preflight.fixture_blocker" in decision["blockers"]
    assert "rescue_preflight.rescue_proposal_committed" in decision["blockers"]
    assert decision["activation_stage_after_decision"] == "shadow"
    assert decision["rescue_proposal_committed"] is False


def test_rescue_stage_decision_rejects_review_overclaim() -> None:
    from app.rescue.application.read_only_stage_promotion import (
        build_rescue_read_only_stage_promotion_decision,
    )

    decision = build_rescue_read_only_stage_promotion_decision(
        rescue_preflight_report=_preflight(),
        human_review_decision=_review(
            rescue_proposal_approved=True,
            scope_keys={"user_id": "user-a"},
        ),
    )

    assert decision["status"] == "blocked"
    assert "human_review_decision.rescue_proposal_approved" in decision["blockers"]
    assert "human_review_decision.scope_keys_missing:workspace_id" in decision[
        "blockers"
    ]
    assert decision["stage_change_recorded"] is False


def test_rescue_stage_decision_runner_requires_artifact_inputs(
    tmp_path: Path,
) -> None:
    preflight_path = tmp_path / "rescue_preflight.json"
    review_path = tmp_path / "review.json"
    output_path = tmp_path / "decision.json"
    preflight_path.write_text(json.dumps(_preflight()), encoding="utf-8")
    review_path.write_text(json.dumps(_review()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_rescue_read_only_stage_promotion.py"),
            "--rescue-preflight-json",
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
    assert artifact["artifact_type"] == "rescue_read_only_runtime_stage_decision"
    assert artifact["status"] == "approved"
    assert artifact["real_artifact_input_required"] is True
