from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _option_packet() -> dict[str, object]:
    from app.rescue.application.no_commit_viability import (
        build_rescue_no_commit_viability_shadow_packet,
    )
    from app.rescue.application.option_generation_shadow import (
        build_rescue_option_generation_shadow_packet,
    )

    viability = build_rescue_no_commit_viability_shadow_packet(
        rescue_context_projection={
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
        },
        current_budget_view={
            "base_budget_kcal": 1800,
            "effective_budget_kcal": 1800,
            "meal_consumption_total_kcal": 2100,
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
    return build_rescue_option_generation_shadow_packet(
        viability_shadow_packet=viability,
    )


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_runner_writes_sanitized_proposal_shaping_input_packet(tmp_path: Path) -> None:
    option_path = tmp_path / "option.json"
    budget_path = tmp_path / "budget_context.json"
    body_plan_path = tmp_path / "body_plan_context.json"
    history_path = tmp_path / "rescue_history_context.json"
    suppression_path = tmp_path / "suppression_context.json"
    output_path = tmp_path / "proposal_input.json"
    _write_json(option_path, _option_packet())
    _write_json(
        budget_path,
        {
            "current_date": "2026-05-09",
            "overshoot_kcal": 300,
            "raw_trace": {"hidden": "budget raw trace"},
        },
    )
    _write_json(
        body_plan_path,
        {
            "safety_floor_kcal": 1200,
            "target_days_count": 5,
            "raw_body_plan": "hidden body plan detail",
        },
    )
    _write_json(
        history_path,
        {
            "recent_rescue_count": 1,
            "summary": "prior rescue was accepted",
            "proposal_id": "hidden-history-proposal",
        },
    )
    _write_json(
        suppression_path,
        [
            {
                "trigger_type": "rescue_nudge",
                "summary": "dismissed once",
                "candidate_copy": "hidden copy",
            }
        ],
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_rescue_proposal_shaping_input_shadow_packet.py"),
            "--option-generation-shadow-packet",
            str(option_path),
            "--budget-context-json",
            str(budget_path),
            "--body-plan-context-json",
            str(body_plan_path),
            "--rescue-history-context-json",
            str(history_path),
            "--suppression-context-json",
            str(suppression_path),
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
    serialized = json.dumps(packet, ensure_ascii=False)
    assert packet["artifact_type"] == "rescue_proposal_shaping_input_shadow_packet"
    assert packet["status"] == "pass"
    assert packet["option_generation_shadow_packet_used"] is True
    assert packet["live_llm_invoked"] is False
    assert packet["provider_called"] is False
    assert packet["runtime_effect_allowed"] is False
    assert packet["proposal_card"] is None
    assert packet["proposal_headline"] is None
    assert packet["proposal_summary"] is None
    assert packet["coaching_frame"] is None
    assert packet["quick_action_posture"] is None
    assert packet["candidate_copy"] is None
    assert packet["send_or_skip"] is None
    assert packet["primary_actions"] == []
    assert packet["proposal_committed"] is False
    assert packet["day_budget_mutated"] is False
    assert packet["manager_context_injected"] is False
    assert packet["durable_memory_written"] is False
    assert packet["shaping_input_envelope"]["deterministic_option"] == {
        "recommended_days": 2,
        "daily_kcal_adjustment": -150,
        "cap_mode": "standard_15_percent",
        "special_posture": "standard_spread",
        "recovery_viability": "viable",
        "guardrail_notes": [
            "daily_cap_denominator_is_base_budget",
            "safety_floor_checked",
            "proposal_required_before_commit",
        ],
    }
    assert packet["shaping_input_envelope"]["review_context"] == {
        "budget_context": {
            "current_date": "2026-05-09",
            "overshoot_kcal": 300,
        },
        "body_plan_context": {
            "safety_floor_kcal": 1200,
            "target_days_count": 5,
        },
        "rescue_history_context": {
            "recent_rescue_count": 1,
            "summary": "prior rescue was accepted",
        },
        "suppression_context": [
            {"trigger_type": "rescue_nudge", "summary": "dismissed once"}
        ],
    }
    assert "budget raw trace" not in serialized
    assert "hidden body plan detail" not in serialized
    assert "hidden-history-proposal" not in serialized
    assert "hidden copy" not in serialized


def test_runner_writes_blocked_packet_for_context_authority_and_upstream_copy_drift(
    tmp_path: Path,
) -> None:
    option = _option_packet()
    option["proposal_headline"] = "Do not surface this."
    option["primary_actions"] = ["accept_rescue_plan"]
    option_path = tmp_path / "option.json"
    budget_path = tmp_path / "budget_context.json"
    output_path = tmp_path / "blocked_proposal_input.json"
    _write_json(option_path, option)
    _write_json(budget_path, {"day_budget_mutated": True})

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_rescue_proposal_shaping_input_shadow_packet.py"),
            "--option-generation-shadow-packet",
            str(option_path),
            "--budget-context-json",
            str(budget_path),
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
    assert packet["option_generation_shadow_packet_used"] is False
    assert packet["shaping_input_envelope"] == {}
    assert "option_generation_shadow_packet.proposal_headline" in packet["blockers"]
    assert "option_generation_shadow_packet.primary_actions" in packet["blockers"]
    assert "budget_context.day_budget_mutated" in packet["blockers"]
    assert packet["proposal_headline"] is None
    assert packet["primary_actions"] == []
    assert packet["live_llm_invoked"] is False
    assert packet["provider_called"] is False
    assert packet["runtime_effect_allowed"] is False
    assert packet["proposal_committed"] is False
    assert packet["day_budget_mutated"] is False
