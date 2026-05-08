from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_bootstrap_same_truth_gate import (
    BOOTSTRAP_SAME_TRUTH_READY_STATUS,
    build_bootstrap_same_truth_gate_artifact,
)


def _browser_smoke(*, status: str = "pass") -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_product_pages_browser_smoke",
        "smoke_id": "accurate_intake_product_pages_browser_smoke_v1",
        "status": status,
        "browser_executed": True,
        "body_page_loaded": True,
        "body_active_plan_rendered": True,
        "body_plan_form_saved": True,
        "body_plan_readback_checked": True,
        "body_plan_read_model_fields_rendered": True,
        "body_budget_read_models_rendered": True,
        "body_manual_target_saved": True,
        "body_manual_target_read_model_rendered": True,
        "today_manual_target_readback_checked": True,
        "body_session_status_rendered": True,
        "today_session_status_rendered": True,
        "body_no_debug_trace": True,
        "today_no_debug_trace": True,
        "product_cjk_copy_rendered": True,
        "body_plan_read_model_values": {
            "daily_target": "1550 kcal",
            "tdee": "1819 kcal",
            "current_weight": "70 kg",
            "target_weight": "65 kg",
            "activity": "light",
            "goal": "Lose weight",
            "weight_history": "2026-05-08 | 70.4 kg",
        },
        "body_budget_read_model_values": {
            "active_target": "1550 kcal",
            "consumed": "400 kcal",
            "remaining": "1150 kcal",
            "estimated_deficit": "269 kcal",
            "effective_budget": "1550 kcal",
            "weekly_progress": "400 kcal consumed",
        },
    }


def _ledger(*, upstream_status: str = "green") -> dict[str, object]:
    return {
        "gates": [
            {
                "gate_id": "rt6_bootstrap_no_plan_body_closure",
                "title": "Bootstrap, no-plan, and body read/write closure",
                "status": upstream_status,
                "pass_type": "runtime_backed",
            }
        ]
    }


def test_bootstrap_same_truth_gate_accepts_bootstrap_browser_evidence_when_upstream_green() -> None:
    artifact = build_bootstrap_same_truth_gate_artifact(
        browser_smoke_artifact=_browser_smoke(),
        manager_runtime_gate_ledger=_ledger(),
    )

    assert artifact["status"] == BOOTSTRAP_SAME_TRUTH_READY_STATUS
    assert artifact["pass_type"] == "browser_executed"
    assert artifact["journeys"] == ["A"]
    assert artifact["upstream_runtime_gate"] == "rt6_bootstrap_no_plan_body_closure"
    assert artifact["summary"]["required_browser_flag_count"] >= 8
    assert artifact["summary"]["upstream_gate_green"] is True
    assert artifact["blockers"] == []


def test_bootstrap_same_truth_gate_blocks_missing_browser_truth_or_non_green_upstream() -> None:
    browser_smoke = _browser_smoke(status="blocked")
    browser_smoke["body_plan_form_saved"] = False
    browser_smoke["today_manual_target_readback_checked"] = False
    artifact = build_bootstrap_same_truth_gate_artifact(
        browser_smoke_artifact=browser_smoke,
        manager_runtime_gate_ledger=_ledger(upstream_status="pending"),
    )

    assert artifact["status"] == "blocked"
    assert "browser_smoke.unexpected_status:blocked" in artifact["blockers"]
    assert "browser_smoke.body_plan_form_saved_not_true" in artifact["blockers"]
    assert "browser_smoke.today_manual_target_readback_checked_not_true" in artifact["blockers"]
    assert "upstream_gate.rt6_bootstrap_no_plan_body_closure_not_green:pending" in artifact["blockers"]


def test_bootstrap_same_truth_gate_cli_writes_output(tmp_path: Path, capsys) -> None:
    from scripts.build_accurate_intake_bootstrap_same_truth_gate import main

    browser_smoke_path = tmp_path / "browser-smoke.json"
    ledger_path = tmp_path / "manager-runtime-gate-ledger.json"
    output_path = tmp_path / "bootstrap-same-truth-gate.json"
    browser_smoke_path.write_text(json.dumps(_browser_smoke()), encoding="utf-8")
    ledger_path.write_text(json.dumps(_ledger()), encoding="utf-8")

    exit_code = main(
        [
            "--browser-smoke-json",
            str(browser_smoke_path),
            "--manager-runtime-gate-ledger-json",
            str(ledger_path),
            "--output",
            str(output_path),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed["status"] == BOOTSTRAP_SAME_TRUTH_READY_STATUS
    assert artifact["status"] == BOOTSTRAP_SAME_TRUTH_READY_STATUS
