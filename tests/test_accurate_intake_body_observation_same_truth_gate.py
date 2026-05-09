from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_body_observation_same_truth_gate import (
    BODY_OBSERVATION_SAME_TRUTH_READY_STATUS,
    REQUIRED_BROWSER_FLAGS,
    build_body_observation_same_truth_gate_artifact,
)


def _passing_browser_smoke() -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_product_pages_browser_smoke",
        "smoke_id": "accurate_intake_product_pages_browser_smoke_v1",
        "status": "pass",
        "browser_executed": True,
        "body_active_plan_rendered": True,
        "body_weight_checkin_saved": True,
        "body_latest_weight_rendered_from_backend": True,
        "body_weight_history_date_scoped_readback": True,
        "body_plan_readback_checked": True,
        "body_manual_target_read_model_rendered": True,
        "today_manual_target_readback_checked": True,
        "body_plan_read_model_values": {
            "daily_target": "1550 kcal",
            "current_weight": "70 kg",
            "weight_history": "2026-05-05 | 70.4 kg",
        },
        "body_budget_read_model_values": {
            "active_target": "1550 kcal",
            "remaining": "1150 kcal",
        },
    }


def _rt6_green_ledger() -> dict[str, object]:
    return {
        "gates": [
            {
                "gate_id": "rt6_bootstrap_no_plan_body_closure",
                "status": "green",
                "pass_type": "runtime_backed",
                "title": "Bootstrap, no-plan, and body read/write closure",
            }
        ]
    }


def test_body_observation_same_truth_gate_accepts_rt6_green_browser_truth() -> None:
    artifact = build_body_observation_same_truth_gate_artifact(
        browser_smoke_artifact=_passing_browser_smoke(),
        manager_runtime_gate_ledger=_rt6_green_ledger(),
    )

    assert artifact["artifact_type"] == "accurate_intake_body_observation_same_truth_gate"
    assert artifact["status"] == BODY_OBSERVATION_SAME_TRUTH_READY_STATUS
    assert artifact["pass_type"] == "browser_executed"
    assert artifact["browser_executed"] is True
    assert artifact["upstream_runtime_gate"] == "rt6_bootstrap_no_plan_body_closure"
    assert artifact["journeys"] == ["G", "H"]
    assert artifact["blockers"] == []
    assert artifact["summary"]["required_browser_flag_count"] == len(REQUIRED_BROWSER_FLAGS)
    assert artifact["summary"]["all_required_browser_flags_true"] is True
    assert artifact["summary"]["upstream_gate_green"] is True
    assert artifact["browser_truth"]["body_latest_weight_rendered_from_backend"] is True
    assert artifact["browser_truth"]["today_manual_target_readback_checked"] is True
    assert "product_readiness_claimed" not in artifact
    assert "private_self_use_approved" not in artifact


def test_body_observation_same_truth_gate_blocks_when_rt6_not_green() -> None:
    artifact = build_body_observation_same_truth_gate_artifact(
        browser_smoke_artifact=_passing_browser_smoke(),
        manager_runtime_gate_ledger={
            "gates": [
                {
                    "gate_id": "rt6_bootstrap_no_plan_body_closure",
                    "status": "pending",
                    "pass_type": "runtime_backed",
                }
            ]
        },
    )

    assert artifact["status"] == "blocked"
    assert "upstream_gate.rt6_bootstrap_no_plan_body_closure_not_green:pending" in artifact["blockers"]


def test_body_observation_same_truth_gate_blocks_when_browser_truth_missing() -> None:
    broken = _passing_browser_smoke()
    broken["body_weight_history_date_scoped_readback"] = False

    artifact = build_body_observation_same_truth_gate_artifact(
        browser_smoke_artifact=broken,
        manager_runtime_gate_ledger=_rt6_green_ledger(),
    )

    assert artifact["status"] == "blocked"
    assert "browser_smoke.body_weight_history_date_scoped_readback_not_true" in artifact["blockers"]


def test_body_observation_same_truth_gate_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_body_observation_same_truth_gate import main

    browser_path = tmp_path / "browser-smoke.json"
    ledger_path = tmp_path / "manager-runtime-gate-ledger.json"
    output_path = tmp_path / "body-observation-same-truth-gate.json"
    browser_path.write_text(json.dumps(_passing_browser_smoke(), ensure_ascii=False), encoding="utf-8")
    ledger_path.write_text(json.dumps(_rt6_green_ledger(), ensure_ascii=False), encoding="utf-8")

    exit_code = main(
        [
            "--browser-smoke-json",
            str(browser_path),
            "--manager-runtime-gate-ledger-json",
            str(ledger_path),
            "--output",
            str(output_path),
        ]
    )
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == BODY_OBSERVATION_SAME_TRUTH_READY_STATUS


def test_body_observation_same_truth_gate_source_stays_out_of_fooddb_live_and_mutation_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_body_observation_same_truth_gate.py"),
        Path("scripts/build_accurate_intake_body_observation_same_truth_gate.py"),
    ]
    combined_source = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "Tavily",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "live_llm_invoked = True",
        "web_tavily_used = True",
        "mutation_changed = True",
    ):
        assert fragment not in combined_source


def test_ci_runs_body_observation_same_truth_gate() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "tests/test_accurate_intake_body_observation_same_truth_gate.py" in workflow
