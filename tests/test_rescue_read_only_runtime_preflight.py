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
        "activation_stage_after_decision": "read_only_runtime",
        "stage_change_recorded": True,
        "manual_promotion_approved": True,
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
        "no_go_flags": {"rescue_proposal_committed": False},
    }
    decision.update(overrides)
    return decision


def _rescue_context(**overrides: object) -> dict[str, object]:
    context: dict[str, object] = {
        "artifact_type": "rescue_shadow_summary_context_projection",
        "status": "pass",
        "blockers": [],
        "memory_summary_projection_used": True,
        "runtime_effect_allowed": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "meal_thread_mutated": False,
        "durable_memory_written": False,
        "manager_context_injected": False,
        "proactive_sent": False,
        "recommendation_served": False,
    }
    context.update(overrides)
    return context


def _viability(**overrides: object) -> dict[str, object]:
    packet: dict[str, object] = {
        "artifact_type": "rescue_no_commit_viability_shadow_packet",
        "status": "pass",
        "blockers": [],
        "rescue_context_projection_used": True,
        "recovery_viability": "viable",
        "proposal_card": None,
        "candidate_copy": None,
        "send_or_skip": None,
        "primary_actions": [],
        "runtime_effect_allowed": False,
        "recommendation_posture_updated": False,
        "ledger_entry_created": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "meal_thread_mutated": False,
        "durable_memory_written": False,
        "manager_context_injected": False,
        "proactive_sent": False,
        "recommendation_served": False,
    }
    packet.update(overrides)
    return packet


def test_preflight_records_rescue_read_only_runtime_candidate_without_commit() -> None:
    from app.rescue.application.read_only_runtime_preflight import (
        build_rescue_read_only_runtime_preflight_report,
    )

    report = build_rescue_read_only_runtime_preflight_report(
        memory_stage_promotion_decision=_memory_stage_decision(),
        rescue_context_projection=_rescue_context(),
        no_commit_viability_packet=_viability(),
    )

    assert report["artifact_type"] == "rescue_read_only_runtime_preflight_report"
    assert report["status"] == "pass"
    assert report["capability"] == "rescue"
    assert report["current_stage"] == "shadow"
    assert report["target_stage"] == "read_only_runtime"
    assert report["dependency_satisfied"] == "long_term_memory.read_only_runtime"
    assert report["source_stage_promotion_fixture_kind"] == (
        "synthetic_merge_safe_contract_fixture"
    )
    assert report["rescue_read_only_runtime_promoted"] is False
    assert report["manual_promotion_review_allowed"] is True
    assert report["automatic_stage_promotion_allowed"] is False
    assert report["rescue_proposal_committed"] is False
    assert report["proposal_committed"] is False
    assert report["ledger_entry_created"] is False
    assert report["day_budget_mutated"] is False
    assert report["manager_context_packet_changed"] is False


def test_preflight_blocks_pending_memory_stage_dependency() -> None:
    from app.rescue.application.read_only_runtime_preflight import (
        build_rescue_read_only_runtime_preflight_report,
    )

    report = build_rescue_read_only_runtime_preflight_report(
        memory_stage_promotion_decision=_memory_stage_decision(
            status="pending_review",
            activation_stage_after_decision="shadow",
            manual_promotion_approved=False,
        ),
        rescue_context_projection=_rescue_context(),
        no_commit_viability_packet=_viability(),
    )

    assert report["status"] == "blocked"
    assert "memory_stage_promotion.status_not_approved" in report["blockers"]
    assert "memory_stage_promotion.activation_stage_not_read_only_runtime" in report[
        "blockers"
    ]
    assert report["manual_promotion_review_allowed"] is False


def test_preflight_blocks_rescue_context_or_viability_overclaim() -> None:
    from app.rescue.application.read_only_runtime_preflight import (
        build_rescue_read_only_runtime_preflight_report,
    )

    report = build_rescue_read_only_runtime_preflight_report(
        memory_stage_promotion_decision=_memory_stage_decision(
            no_go_flags={"rescue_proposal_committed": True}
        ),
        rescue_context_projection=_rescue_context(proposal_committed=True),
        no_commit_viability_packet=_viability(
            ledger_entry_created=True,
            proposal_card={"proposal_id": "not-allowed"},
        ),
    )

    assert report["status"] == "blocked"
    assert "memory_stage_promotion.no_go_flag_true:rescue_proposal_committed" in report[
        "blockers"
    ]
    assert "rescue_context_projection.proposal_committed" in report["blockers"]
    assert "no_commit_viability_packet.ledger_entry_created" in report["blockers"]
    assert "no_commit_viability_packet.proposal_card_present" in report["blockers"]
    assert report["proposal_committed"] is False
    assert report["ledger_entry_created"] is False


def test_preflight_runner_requires_artifact_inputs(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory_stage_decision.json"
    context_path = tmp_path / "rescue_context.json"
    viability_path = tmp_path / "viability.json"
    output_path = tmp_path / "rescue_preflight.json"
    memory_path.write_text(json.dumps(_memory_stage_decision()), encoding="utf-8")
    context_path.write_text(json.dumps(_rescue_context()), encoding="utf-8")
    viability_path.write_text(json.dumps(_viability()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_rescue_read_only_runtime_preflight.py"),
            "--memory-stage-promotion-decision-json",
            str(memory_path),
            "--rescue-context-projection-json",
            str(context_path),
            "--no-commit-viability-json",
            str(viability_path),
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
    assert artifact["artifact_type"] == "rescue_read_only_runtime_preflight_report"
    assert artifact["status"] == "pass"
    assert artifact["real_artifact_input_required"] is True
