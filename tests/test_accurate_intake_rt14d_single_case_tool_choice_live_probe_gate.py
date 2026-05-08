from __future__ import annotations

import importlib
import json
from pathlib import Path

from scripts.build_accurate_intake_rt14d_single_case_tool_choice_live_probe_gate import (
    build_rt14d_single_case_tool_choice_live_probe_gate,
)


def _build_live_single_case_report(tmp_path: Path) -> dict:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")
    return module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic_single_case.json",
        db_path=tmp_path / "accurate_intake_mvp_live_diagnostic_single_case.sqlite3",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="live",
        live_invoked=True,
        stage="single_case_live_probe",
        case_id="today_consumed_query_only",
    )


def test_rt14d_single_case_tool_choice_live_probe_gate_passes_for_query_only_case(tmp_path: Path) -> None:
    source = _build_live_single_case_report(tmp_path)

    artifact = build_rt14d_single_case_tool_choice_live_probe_gate(
        live_diagnostic_artifact=source,
    )

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt14d_single_case_tool_choice_live_probe"
    assert artifact["summary"]["required_stage_id"] == "single_case_live_probe"
    assert artifact["summary"]["required_case_id"] == "today_consumed_query_only"
    assert artifact["summary"]["required_result_kind"] == "strict_pass_first_attempt"
    assert artifact["summary"]["non_claim_flags_preserved"] is True


def test_rt14d_single_case_tool_choice_live_probe_gate_blocks_non_live_artifact(tmp_path: Path) -> None:
    source = _build_live_single_case_report(tmp_path)
    source["provider_mode"] = "fake_provider_contract_test"
    source["live_invoked"] = False

    artifact = build_rt14d_single_case_tool_choice_live_probe_gate(
        live_diagnostic_artifact=source,
    )

    assert artifact["status"] == "fail"
    assert "provider_mode_not_live" in artifact["blockers"]
    assert "live_not_invoked" in artifact["blockers"]


def test_rt14d_single_case_tool_choice_live_probe_gate_blocks_query_case_mutation(tmp_path: Path) -> None:
    source = _build_live_single_case_report(tmp_path)
    source["cases"][0]["turns"][0]["state_delta"]["canonical_commit"] = True

    artifact = build_rt14d_single_case_tool_choice_live_probe_gate(
        live_diagnostic_artifact=source,
    )

    assert artifact["status"] == "fail"
    assert "query_only_mutated_state" in artifact["blockers"]


def test_rt14d_single_case_tool_choice_live_probe_gate_cli_writes_json(tmp_path: Path) -> None:
    source = _build_live_single_case_report(tmp_path)
    source_path = tmp_path / "source.json"
    source_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "accurate_intake_rt14d_single_case_tool_choice_live_probe_gate.json"

    from scripts.build_accurate_intake_rt14d_single_case_tool_choice_live_probe_gate import main

    exit_code = main(
        [
            "--source-artifact",
            str(source_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "accurate_intake_rt14d_single_case_tool_choice_live_probe_gate"
    assert payload["status"] == "pass"
