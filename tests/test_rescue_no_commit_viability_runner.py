from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _rescue_context(**overrides: object) -> dict[str, object]:
    context: dict[str, object] = {
        "artifact_type": "rescue_shadow_summary_context_projection",
        "status": "pass",
        "memory_summary_projection_used": True,
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


def _budget(consumed: int = 2100, effective: int = 1800) -> dict[str, int]:
    return {
        "base_budget_kcal": 1800,
        "effective_budget_kcal": effective,
        "meal_consumption_total_kcal": consumed,
    }


def _body_plan(days: int = 3) -> dict[str, object]:
    return {
        "safety_floor_kcal": 1200,
        "target_days": [
            {
                "local_date": f"2026-05-{10 + index:02d}",
                "base_budget_kcal": 1800,
                "calibration_adjustment_total_kcal": 0,
            }
            for index in range(days)
        ],
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_runner_writes_rescue_no_commit_viability_packet(tmp_path: Path) -> None:
    context_path = tmp_path / "rescue_context.json"
    budget_path = tmp_path / "budget.json"
    body_plan_path = tmp_path / "body_plan.json"
    open_proposals_path = tmp_path / "open_proposals.json"
    output_path = tmp_path / "rescue_viability.json"
    _write_json(context_path, _rescue_context())
    _write_json(budget_path, _budget(consumed=2100))
    _write_json(body_plan_path, _body_plan(days=3))
    _write_json(open_proposals_path, {"open_rescue_proposal_count": 0})

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_rescue_no_commit_viability_shadow_packet.py"),
            "--rescue-summary-context-projection",
            str(context_path),
            "--current-budget-view-json",
            str(budget_path),
            "--active-body-plan-view-json",
            str(body_plan_path),
            "--open-proposals-view-json",
            str(open_proposals_path),
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    packet = json.loads(output_path.read_text(encoding="utf-8"))
    assert packet["artifact_type"] == "rescue_no_commit_viability_shadow_packet"
    assert packet["status"] == "pass"
    assert packet["recovery_viability"] == "viable"
    assert packet["daily_recovery_kcal"] == 100
    assert packet["rescue_context_projection_used"] is True
    assert packet["proposal_card"] is None
    assert packet["candidate_copy"] is None
    assert packet["send_or_skip"] is None
    assert packet["primary_actions"] == []
    assert packet["runtime_effect_allowed"] is False
    assert packet["rescue_committed"] is False
    assert packet["proposal_committed"] is False
    assert packet["day_budget_mutated"] is False
    assert packet["body_plan_mutated"] is False
    assert packet["meal_thread_mutated"] is False
    assert packet["manager_context_injected"] is False
    assert packet["durable_memory_written"] is False


def test_runner_writes_blocked_packet_for_context_claim_drift_and_missing_budget(
    tmp_path: Path,
) -> None:
    context_path = tmp_path / "rescue_context.json"
    budget_path = tmp_path / "budget.json"
    body_plan_path = tmp_path / "body_plan.json"
    open_proposals_path = tmp_path / "open_proposals.json"
    output_path = tmp_path / "blocked_rescue_viability.json"
    _write_json(context_path, _rescue_context(proposal_committed=True))
    _write_json(budget_path, {})
    _write_json(body_plan_path, _body_plan(days=3))
    _write_json(open_proposals_path, {"open_rescue_proposal_count": 0})

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_rescue_no_commit_viability_shadow_packet.py"),
            "--rescue-summary-context-projection",
            str(context_path),
            "--current-budget-view-json",
            str(budget_path),
            "--active-body-plan-view-json",
            str(body_plan_path),
            "--open-proposals-view-json",
            str(open_proposals_path),
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    packet = json.loads(output_path.read_text(encoding="utf-8"))
    assert packet["status"] == "blocked"
    assert packet["recovery_viability"] == "blocked"
    assert "rescue_context_projection.proposal_committed" in packet["blockers"]
    assert "missing_budget_view" in packet["blockers"]
    assert packet["rescue_context_projection_used"] is False
    assert packet["target_day_checks"] == []
    assert packet["proposal_card"] is None
    assert packet["candidate_copy"] is None
    assert packet["send_or_skip"] is None
    assert packet["runtime_effect_allowed"] is False
    assert packet["proposal_committed"] is False
    assert packet["day_budget_mutated"] is False
