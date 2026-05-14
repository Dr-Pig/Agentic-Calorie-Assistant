from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _rescue_context() -> dict[str, object]:
    return {
        "artifact_type": "rescue_shadow_summary_context_projection",
        "status": "pass",
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


def _viability_packet(*, consumed: int = 2100) -> dict[str, object]:
    from app.rescue.application.no_commit_viability import (
        build_rescue_no_commit_viability_shadow_packet,
    )

    return build_rescue_no_commit_viability_shadow_packet(
        rescue_context_projection=_rescue_context(),
        current_budget_view={
            "base_budget_kcal": 1800,
            "effective_budget_kcal": 1800,
            "meal_consumption_total_kcal": consumed,
        },
        active_body_plan_view={
            "safety_floor_kcal": 1200,
            "target_days": [
                {
                    "local_date": f"2026-05-{10 + index:02d}",
                    "base_budget_kcal": 1800,
                    "calibration_adjustment_total_kcal": 0,
                }
                for index in range(5)
            ],
        },
        open_proposals_view={"open_rescue_proposal_count": 0},
    )


def _run_option_runner(
    tmp_path: Path,
    viability_packet: dict[str, object],
    *,
    adjustment_request: str | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    input_path = tmp_path / "viability.json"
    output_path = tmp_path / "option.json"
    input_path.write_text(json.dumps(viability_packet), encoding="utf-8")

    command = [
            sys.executable,
            str(ROOT / "scripts" / "build_rescue_option_generation_shadow_packet.py"),
            "--viability-shadow-packet",
            str(input_path),
            "--output",
            str(output_path),
    ]
    if adjustment_request:
        command.extend(["--adjustment-request", adjustment_request])

    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else {}
    return result, payload


def test_runner_writes_rescue_option_generation_packet(tmp_path: Path) -> None:
    result, packet = _run_option_runner(tmp_path, _viability_packet(consumed=2100))

    assert result.returncode == 0, result.stderr
    assert packet["artifact_type"] == "rescue_option_generation_shadow_packet"
    assert packet["status"] == "pass"
    assert packet["viability_shadow_packet_used"] is True
    assert packet["rescue_needed"] is True
    assert packet["recovery_viability"] == "viable"
    assert packet["recommended_days"] == 2
    assert packet["daily_kcal_adjustment"] == -150
    assert packet["proposal_card"] is None
    assert packet["proposal_headline"] is None
    assert packet["proposal_summary"] is None
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


def test_runner_writes_shorter_request_with_strict_fifteen_cap_packet(
    tmp_path: Path,
) -> None:
    result, packet = _run_option_runner(
        tmp_path,
        _viability_packet(consumed=2520),
        adjustment_request="shorter_more_aggressive",
    )

    assert result.returncode == 0, result.stderr
    assert packet["status"] == "pass"
    assert packet["cap_mode"] == "standard_15_percent"
    assert packet["recommended_days"] == 3
    assert packet["daily_kcal_adjustment"] == -240
    assert packet["proposal_card"] is None
    assert packet["candidate_copy"] is None
    assert packet["runtime_effect_allowed"] is False
    assert packet["proposal_committed"] is False


def test_runner_writes_blocked_packet_for_upstream_claim_drift(
    tmp_path: Path,
) -> None:
    viability = _viability_packet(consumed=2100)
    viability["proposal_committed"] = True

    result, packet = _run_option_runner(tmp_path, viability)

    assert result.returncode == 1
    assert packet["status"] == "blocked"
    assert packet["recovery_viability"] == "blocked"
    assert "viability_shadow_packet.proposal_committed" in packet["blockers"]
    assert packet["viability_shadow_packet_used"] is False
    assert packet["recommended_days"] is None
    assert packet["daily_kcal_adjustment"] is None
    assert packet["proposal_card"] is None
    assert packet["candidate_copy"] is None
    assert packet["send_or_skip"] is None
    assert packet["primary_actions"] == []
    assert packet["runtime_effect_allowed"] is False
    assert packet["proposal_committed"] is False
    assert packet["day_budget_mutated"] is False
