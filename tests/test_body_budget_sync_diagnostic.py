from __future__ import annotations

import json
from pathlib import Path

from app.composition.body_budget_sync_diagnostic import build_body_budget_sync_diagnostic_artifact


def _summary() -> dict[str, object]:
    return {
        "source_kind": "body_budget_deficit_summary",
        "read_only": True,
        "user_id": 1,
        "local_date": "2026-05-04",
        "active_daily_target_kcal": 1800,
        "recommended_target_kcal": 1800,
        "consumed_kcal": 420,
        "remaining_kcal": 1380,
        "estimated_daily_deficit_kcal": 500,
        "latest_weight_kg": 69.4,
        "latest_weight_observed_at": "2026-05-04T22:30:00",
        "weight_history_count": 2,
        "target_available": True,
        "remaining_available": True,
        "automatic_calibration_enabled": False,
        "rescue_enabled": False,
        "recommendation_enabled": False,
        "proactive_enabled": False,
    }


def test_body_budget_sync_diagnostic_artifact_records_non_claims_and_summary() -> None:
    artifact = build_body_budget_sync_diagnostic_artifact(_summary())

    assert artifact["artifact_type"] == "body_budget_sync_diagnostic"
    assert artifact["claim_scope"] == "local_body_budget_diagnostic"
    assert artifact["local_only"] is True
    assert artifact["diagnostic_only"] is True
    assert artifact["body_budget_summary"]["remaining_kcal"] == 1380
    assert artifact["runtime_truth_changed"]["scope"] == "body_budget_read_model_only"
    assert artifact["live_tool_calling"] is False
    assert artifact["automatic_calibration_enabled"] is False
    assert artifact["rescue_enabled"] is False
    assert artifact["recommendation_enabled"] is False
    assert artifact["proactive_enabled"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False


def test_body_budget_sync_diagnostic_script_writes_artifact(tmp_path: Path) -> None:
    from scripts.run_body_budget_sync_diagnostic import main

    output = tmp_path / "body_budget_sync_diagnostic.json"
    exit_code = main(
        [
            "--output",
            str(output),
            "--summary-json",
            json.dumps(_summary()),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "body_budget_sync_diagnostic"
    assert payload["body_budget_summary"]["latest_weight_kg"] == 69.4
