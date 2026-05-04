from __future__ import annotations

import json
from pathlib import Path

from scripts.run_body_budget_calibration_self_use_journey_smoke import (
    build_body_budget_calibration_self_use_journey_report,
    main,
)

FORBIDDEN_HISTORY_FIELDS = {"metadata", "trace_envelope", "proposal_policy_packet", "options", "effect_payload"}


def test_body_budget_calibration_self_use_journey_smoke_exercises_closed_loop(tmp_path: Path) -> None:
    report = build_body_budget_calibration_self_use_journey_report(
        db_path=tmp_path / "body_budget_calibration_self_use.sqlite3",
        reset_db=True,
    )

    assert report["artifact_type"] == "body_budget_calibration_self_use_journey_smoke"
    assert report["status"] == "pass"
    assert report["invariant_blockers"] == []
    assert report["claim_scope"] == "local_deterministic_body_budget_calibration_smoke"
    assert report["private_self_use_approved"] is False
    assert report["product_readiness_claimed"] is False
    assert report["live_tool_calling"] is False
    assert report["automatic_calibration_enabled"] is False
    assert report["proposal_preview"]["workflow_effect"] == "preview_calibration_proposal_without_plan_mutation"
    assert report["proposal_preview"]["proposal_actions_enabled"] is True
    assert report["proposal_preview"]["plan_mutated"] is False
    assert report["proposal_preview"]["ledger_mutated"] is False
    assert report["proposal_inbox_before_accept"]["open_count"] == 1
    before_history_item = report["proposal_history_before_accept"]["proposals"][0]
    assert report["proposal_history_before_accept"]["history_count"] == 1
    assert before_history_item["proposal_status"] == "open"
    assert FORBIDDEN_HISTORY_FIELDS.isdisjoint(before_history_item)
    assert report["boundaries"]["history_projection_safe_before_accept"] is True
    assert report["raw_text_apply_attempt"] == {
        "workflow_effect": "calibration_action_unavailable_without_state_mutation",
        "proposal_status_after_attempt": "open",
        "plan_mutated": False,
        "ledger_mutated": False,
        "proposal_container_id_supplied": False,
        "calibration_action_supplied": False,
        "raw_text_authorized_mutation": False,
    }
    assert report["proposal_action"]["workflow_effect"] == "apply_calibration_proposal_action_with_state_mutation"
    assert report["proposal_action"]["proposal_status"] == "accepted"
    assert report["proposal_action"]["plan_mutated"] is True
    assert report["proposal_action"]["ledger_mutated"] is True
    assert report["proposal_inbox_after_accept"]["open_count"] == 0

    history_item = report["proposal_history_after_accept"]["proposals"][0]
    assert history_item["proposal_status"] == "accepted"
    assert history_item["primary_option_summary"]
    assert FORBIDDEN_HISTORY_FIELDS.isdisjoint(history_item)
    assert report["boundaries"]["history_projection_safe_after_accept"] is True

    sync = report["post_accept_read_model_sync"]
    assert sync["current_budget_kcal"] == sync["active_body_plan_daily_budget_kcal"]
    assert sync["effective_budget_kcal"] == sync["current_budget_kcal"]
    assert sync["current_budget_remaining_kcal"] == sync["effective_budget_remaining_kcal"]
    assert sync["weekly_progress_current_day_target_kcal"] == sync["current_budget_kcal"]
    assert sync["weekly_progress_current_day_consumed_kcal"] == sync["current_budget_consumed_kcal"]
    assert sync["weekly_progress_current_day_remaining_kcal"] == sync["current_budget_remaining_kcal"]
    assert sync["weekly_progress_latest_weight_kg"] == 69.9
    assert sync["calibration_adjustment_entry_count"] == 0


def test_body_budget_calibration_self_use_journey_smoke_cli_writes_artifact(tmp_path: Path) -> None:
    output = tmp_path / "body_budget_calibration_self_use_journey.json"
    db_path = tmp_path / "body_budget_calibration_self_use.sqlite3"

    exit_code = main(["--db-path", str(db_path), "--output", str(output), "--reset-db"])

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["proposal_history_after_accept"]["history_count"] == 1


def test_body_budget_calibration_self_use_journey_smoke_cli_resets_by_default_and_repeats(tmp_path: Path) -> None:
    output = tmp_path / "body_budget_calibration_self_use_journey.json"
    db_path = tmp_path / "body_budget_calibration_self_use.sqlite3"
    args = ["--db-path", str(db_path), "--output", str(output)]

    first_exit_code = main(args)
    second_exit_code = main(args)

    assert first_exit_code == 0
    assert second_exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["invariant_blockers"] == []
