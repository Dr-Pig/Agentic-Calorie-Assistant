from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "run_rescue_executable_pack.py"
SPEC = importlib.util.spec_from_file_location("run_rescue_executable_pack", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
run_rescue_executable_pack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_rescue_executable_pack)


def _case_map() -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    executable_pack = run_rescue_executable_pack.load_executable_pack()
    source_pack = run_rescue_executable_pack.load_source_pack()
    executable_cases = {
        str(case["executable_case_id"]): dict(case)
        for case in executable_pack.get("cases", [])
    }
    source_cases = run_rescue_executable_pack._source_case_map(source_pack)
    return executable_cases, source_cases


def test_accept_case_applies_overlay_and_matches_expected_runtime_outcome() -> None:
    executable_cases, source_cases = _case_map()

    result = run_rescue_executable_pack.run_case(
        executable_cases["rescue_accept_executable_001"],
        source_case_map=source_cases,
    )

    assert result["oracle"]["passed"] is True
    assert result["observed_runtime_outcome"]["workflow_effect"] == "accept_and_apply_current_proposal"
    assert result["db_snapshot"]["proposal_status"] == "accepted"
    assert result["db_snapshot"]["ledger_entry_count"] == 3
    assert result["db_snapshot"]["ledger_entry_deltas"] == [-180, -180, -180]


def test_reject_and_defer_cases_reuse_source_utterance_as_reason() -> None:
    executable_cases, source_cases = _case_map()

    reject_result = run_rescue_executable_pack.run_case(
        executable_cases["rescue_reject_executable_001"],
        source_case_map=source_cases,
    )
    defer_result = run_rescue_executable_pack.run_case(
        executable_cases["rescue_defer_executable_001"],
        source_case_map=source_cases,
    )

    assert reject_result["resolved_reason"] == reject_result["source_utterance"]
    assert reject_result["db_snapshot"]["proposal_status"] == "rejected"
    assert reject_result["db_snapshot"]["metadata"]["reason_bridge"]["raw_reason_text"] == reject_result["source_utterance"]

    assert defer_result["resolved_reason"] == defer_result["source_utterance"]
    assert defer_result["db_snapshot"]["proposal_status"] == "deferred_pending_reminder"
    assert defer_result["db_snapshot"]["metadata"]["reason_bridge"]["raw_reason_text"] == defer_result["source_utterance"]


def test_adjust_case_reports_surface_only_runtime_behavior() -> None:
    executable_cases, source_cases = _case_map()

    result = run_rescue_executable_pack.run_case(
        executable_cases["rescue_adjust_executable_001"],
        source_case_map=source_cases,
    )

    assert result["oracle"]["passed"] is False
    assert result["observed_runtime_outcome"]["disposition"] == "adjust"
    assert result["observed_runtime_outcome"]["adjust_direction"] == "longer"
    assert result["observed_runtime_outcome"]["workflow_effect"] == "answer_current_object"
    assert result["observed_runtime_outcome"]["persistence_mode"] == "surface_only"
    assert result["db_snapshot"]["proposal_status"] == "open"
    assert result["response"]["recommended_days"] == 4
    assert result["response"]["daily_kcal_adjustment"] == 135


def test_run_pack_summary_marks_only_adjust_case_as_failed() -> None:
    report = run_rescue_executable_pack.run_pack()

    assert report["summary"]["total_cases"] == 5
    assert report["summary"]["passed_cases"] == 4
    assert report["summary"]["failed_cases"] == 1
    assert report["summary"]["failed_case_ids"] == ["rescue_adjust_executable_001"]
