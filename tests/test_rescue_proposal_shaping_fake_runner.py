from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def _input_packet() -> dict[str, object]:
    from app.rescue.application.no_commit_viability import (
        build_rescue_no_commit_viability_shadow_packet,
    )
    from app.rescue.application.option_generation_shadow import (
        build_rescue_option_generation_shadow_packet,
    )
    from app.rescue.application.proposal_shaping_input_shadow import (
        build_rescue_proposal_shaping_input_shadow_packet,
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
    option = build_rescue_option_generation_shadow_packet(
        viability_shadow_packet=viability,
    )
    return build_rescue_proposal_shaping_input_shadow_packet(
        option_generation_shadow_packet=option,
    )


def _candidate_output() -> dict[str, object]:
    return {
        "proposal_headline": "Fixture headline, not user-facing",
        "proposal_summary": "Fixture summary, not user-facing",
        "coaching_frame": "Fixture frame, not user-facing",
        "recommended_days": 2,
        "daily_kcal_adjustment": -150,
        "cap_mode": "standard_15_percent",
        "special_posture": "standard_spread",
        "rubric": {
            "future_oriented": True,
            "no_shame": True,
            "not_user_facing": True,
            "fixture_only": True,
        },
    }


def test_fake_runner_validates_supplied_output_without_provider_or_raw_output() -> None:
    from app.rescue.application.proposal_shaping_fake_runner import (
        run_rescue_proposal_shaping_fake,
    )

    artifact = run_rescue_proposal_shaping_fake(
        proposal_shaping_input_shadow_packet=_input_packet(),
        candidate_output=_candidate_output(),
    )
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert artifact["artifact_type"] == "rescue_proposal_shaping_fake_runner_artifact"
    assert artifact["status"] == "pass"
    assert artifact["runner_stage"] == "fake"
    assert artifact["candidate_output_supplied"] is True
    assert artifact["candidate_output_consumed"] is True
    assert artifact["raw_candidate_output_included"] is False
    assert artifact["validation"]["status"] == "pass"
    assert artifact["validation"]["fixture_output_validated"] is True
    assert artifact["live_llm_invoked"] is False
    assert artifact["provider_called"] is False
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["proposal_committed"] is False
    assert "Fixture headline, not user-facing" not in serialized
    assert "Fixture summary, not user-facing" not in serialized


def test_fake_runner_reports_validator_failures_without_leaking_values() -> None:
    from app.rescue.application.proposal_shaping_fake_runner import (
        run_rescue_proposal_shaping_fake,
    )

    candidate = _candidate_output()
    candidate["recommended_days"] = 1
    candidate["primary_actions"] = ["accept_rescue_plan"]
    candidate["proposal_card"] = {"title": "Hidden proposal card"}

    artifact = run_rescue_proposal_shaping_fake(
        proposal_shaping_input_shadow_packet=_input_packet(),
        candidate_output=candidate,
    )
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert artifact["status"] == "fail"
    assert artifact["validation_status"] == "fail"
    assert "candidate_output.recommended_days_override" in artifact["blockers"]
    assert "candidate_output.primary_actions_forbidden" in artifact["blockers"]
    assert "candidate_output.proposal_card_forbidden" in artifact["blockers"]
    assert "Hidden proposal card" not in serialized
    assert "accept_rescue_plan" not in serialized
    assert artifact["proposal_committed"] is False
    assert artifact["ledger_entry_created"] is False


def test_fake_runner_blocks_input_packet_drift_before_candidate_consumption() -> None:
    from app.rescue.application.proposal_shaping_fake_runner import (
        run_rescue_proposal_shaping_fake,
    )

    input_packet = _input_packet()
    input_packet["status"] = "blocked"
    candidate = _candidate_output()
    candidate["proposal_headline"] = "Hidden blocked-input headline"

    artifact = run_rescue_proposal_shaping_fake(
        proposal_shaping_input_shadow_packet=input_packet,
        candidate_output=candidate,
    )
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert artifact["status"] == "blocked"
    assert artifact["candidate_output_consumed"] is False
    assert artifact["validation_status"] == "blocked"
    assert "proposal_shaping_input_shadow_packet.status_blocked" in artifact["blockers"]
    assert "Hidden blocked-input headline" not in serialized
    assert artifact["live_llm_invoked"] is False
    assert artifact["provider_called"] is False
    assert artifact["manager_context_injected"] is False


def test_fake_runner_cli_writes_pass_artifact_without_raw_candidate_output(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    input_path = tmp_path / "rescue_proposal_shaping_input_shadow_packet.json"
    candidate_path = tmp_path / "fixture_candidate_output.json"
    output_path = tmp_path / "rescue_proposal_shaping_fake_runner_artifact.json"
    input_path.write_text(json.dumps(_input_packet(), ensure_ascii=False), encoding="utf-8")
    candidate_path.write_text(
        json.dumps(_candidate_output(), ensure_ascii=False),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "build_rescue_proposal_shaping_fake_runner.py"),
            "--proposal-shaping-input-shadow-packet",
            str(input_path),
            "--candidate-output",
            str(candidate_path),
            "--output",
            str(output_path),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    serialized = json.dumps(artifact, ensure_ascii=False)
    assert artifact["artifact_type"] == "rescue_proposal_shaping_fake_runner_artifact"
    assert artifact["status"] == "pass"
    assert artifact["runner_stage"] == "fake"
    assert artifact["validation_status"] == "pass"
    assert artifact["live_llm_invoked"] is False
    assert artifact["provider_called"] is False
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["proposal_committed"] is False
    assert artifact["day_budget_mutated"] is False
    assert "Fixture headline, not user-facing" not in serialized
    assert "Fixture summary, not user-facing" not in serialized


def test_fake_runner_cli_fails_closed_after_writing_validation_artifact(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    input_path = tmp_path / "rescue_proposal_shaping_input_shadow_packet.json"
    candidate_path = tmp_path / "fixture_candidate_output.json"
    output_path = tmp_path / "rescue_proposal_shaping_fake_runner_artifact.json"
    invalid_candidate = _candidate_output()
    invalid_candidate["recommended_days"] = 1
    invalid_candidate["primary_actions"] = ["accept_rescue_plan"]
    invalid_candidate["proposal_card"] = {"title": "Hidden proposal card"}
    input_path.write_text(json.dumps(_input_packet(), ensure_ascii=False), encoding="utf-8")
    candidate_path.write_text(
        json.dumps(invalid_candidate, ensure_ascii=False),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "build_rescue_proposal_shaping_fake_runner.py"),
            "--proposal-shaping-input-shadow-packet",
            str(input_path),
            "--candidate-output",
            str(candidate_path),
            "--output",
            str(output_path),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    serialized = json.dumps(artifact, ensure_ascii=False)
    assert artifact["status"] == "fail"
    assert artifact["validation_status"] == "fail"
    assert "candidate_output.recommended_days_override" in artifact["blockers"]
    assert "candidate_output.primary_actions_forbidden" in artifact["blockers"]
    assert "candidate_output.proposal_card_forbidden" in artifact["blockers"]
    assert artifact["live_llm_invoked"] is False
    assert artifact["provider_called"] is False
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["proposal_committed"] is False
    assert artifact["ledger_entry_created"] is False
    assert "accept_rescue_plan" not in serialized
    assert "Hidden proposal card" not in serialized
