from __future__ import annotations

import importlib
import json
from pathlib import Path
import tempfile

from scripts.build_accurate_intake_rt14e_context_conditioned_live_probe_gate import (
    build_rt14e_context_conditioned_live_probe_gate,
)


def _build_live_single_case_report(*, case_id: str) -> dict:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")
    tmp_root = Path(tempfile.mkdtemp(prefix="rt14e-live-"))
    return module.run_diagnostic(
        output_path=tmp_root / f"{case_id}.json",
        db_path=tmp_root / f"{case_id}.sqlite3",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="live",
        live_invoked=True,
        stage="single_case_live_probe",
        case_id=case_id,
    )


def test_rt14e_context_conditioned_live_probe_gate_passes_for_ready_and_no_plan_cases(tmp_path: Path) -> None:
    ready_source = _build_live_single_case_report(case_id="today_consumed_query_only")
    no_plan_source = _build_live_single_case_report(case_id="no_plan_consumed_without_budget_target")

    artifact = build_rt14e_context_conditioned_live_probe_gate(
        ready_case_artifact=ready_source,
        no_plan_case_artifact=no_plan_source,
    )

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt14e_context_conditioned_live_probe"
    assert artifact["summary"]["required_stage_id"] == "single_case_live_probe"
    assert artifact["summary"]["ready_case_id"] == "today_consumed_query_only"
    assert artifact["summary"]["no_plan_case_id"] == "no_plan_consumed_without_budget_target"


def test_rt14e_context_conditioned_live_probe_gate_blocks_non_live_artifact(tmp_path: Path) -> None:
    ready_source = _build_live_single_case_report(case_id="today_consumed_query_only")
    no_plan_source = _build_live_single_case_report(case_id="no_plan_consumed_without_budget_target")
    no_plan_source["provider_mode"] = "fake_provider_contract_test"
    no_plan_source["live_invoked"] = False

    artifact = build_rt14e_context_conditioned_live_probe_gate(
        ready_case_artifact=ready_source,
        no_plan_case_artifact=no_plan_source,
    )

    assert artifact["status"] == "fail"
    assert "provider_mode_not_live" in artifact["blockers"]
    assert "live_not_invoked" in artifact["blockers"]


def test_rt14e_context_conditioned_live_probe_gate_blocks_missing_context_difference(tmp_path: Path) -> None:
    ready_source = _build_live_single_case_report(case_id="today_consumed_query_only")
    no_plan_source = _build_live_single_case_report(case_id="no_plan_consumed_without_budget_target")
    no_plan_source["cases"][0]["turns"][0]["remaining_budget"]["status"] = "ready"
    no_plan_source["cases"][0]["turns"][0]["remaining_budget"]["daily_target_kcal"] = 1312
    no_plan_source["cases"][0]["turns"][0]["remaining_budget"]["remaining_kcal"] = 1312

    artifact = build_rt14e_context_conditioned_live_probe_gate(
        ready_case_artifact=ready_source,
        no_plan_case_artifact=no_plan_source,
    )

    assert artifact["status"] == "fail"
    assert "context_condition_not_distinguishing_status" in artifact["blockers"]


def test_rt14e_context_conditioned_live_probe_gate_cli_writes_json(tmp_path: Path) -> None:
    ready_source = _build_live_single_case_report(case_id="today_consumed_query_only")
    no_plan_source = _build_live_single_case_report(case_id="no_plan_consumed_without_budget_target")
    ready_source_path = tmp_path / "ready_source.json"
    no_plan_source_path = tmp_path / "no_plan_source.json"
    ready_source_path.write_text(json.dumps(ready_source, ensure_ascii=False), encoding="utf-8")
    no_plan_source_path.write_text(json.dumps(no_plan_source, ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "accurate_intake_rt14e_context_conditioned_live_probe_gate.json"

    from scripts.build_accurate_intake_rt14e_context_conditioned_live_probe_gate import main

    exit_code = main(
        [
            "--ready-case-artifact",
            str(ready_source_path),
            "--no-plan-case-artifact",
            str(no_plan_source_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "accurate_intake_rt14e_context_conditioned_live_probe_gate"
    assert payload["status"] == "pass"
