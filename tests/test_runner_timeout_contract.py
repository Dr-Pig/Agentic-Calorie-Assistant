from __future__ import annotations

from scripts.runner_timeout_contract import apply_runner_timeout_contract
from scripts.run_v2_benchmark_blocking_eval import _build_report as build_benchmark_report
from scripts.run_v2_founder_realism_eval import _build_report as build_founder_report


def test_partial_report_cannot_remain_green() -> None:
    report = {"summary": {"runner_case_status": "pass"}}

    guarded = apply_runner_timeout_contract(
        report,
        expected_total_cases=10,
        completed_cases=3,
        run_mode="full",
    )

    assert guarded["report_status"] == "incomplete"
    assert guarded["final_gate_eligible"] is False
    assert guarded["request_failure_family"] == "partial_report"
    assert guarded["summary"]["runner_case_status"] == "fail"


def test_timeout_report_is_incomplete_and_classified() -> None:
    guarded = apply_runner_timeout_contract(
        {"summary": {"runner_case_status": "pass"}},
        expected_total_cases=5,
        completed_cases=5,
        run_mode="full",
        timed_out=True,
    )

    assert guarded["report_status"] == "incomplete"
    assert guarded["request_failure_family"] == "timeout"
    assert guarded["summary"]["runner_case_status"] == "fail"


def test_shard_report_is_not_final_gate_even_when_cases_pass() -> None:
    guarded = apply_runner_timeout_contract(
        {"summary": {"runner_case_status": "pass"}},
        expected_total_cases=1,
        completed_cases=1,
        run_mode="shard",
    )

    assert guarded["report_status"] == "complete"
    assert guarded["shard_run"] is True
    assert guarded["full_integration"] is False
    assert guarded["final_gate_eligible"] is False
    assert guarded["summary"]["runner_case_status"] == "fail"


def test_full_complete_report_can_be_final_gate_eligible() -> None:
    guarded = apply_runner_timeout_contract(
        {"summary": {"runner_case_status": "pass"}},
        expected_total_cases=2,
        completed_cases=2,
        run_mode="full",
    )

    assert guarded["report_status"] == "complete"
    assert guarded["final_gate_eligible"] is True
    assert guarded["summary"]["runner_case_status"] == "pass"


def test_benchmark_partial_report_marks_incomplete() -> None:
    report = build_benchmark_report(
        base_url="http://test",
        local_date="2026-04-23",
        selected_cases=[{"source_case_id": "case-a", "source_suite": "suite"}, {"source_case_id": "case-b", "source_suite": "suite"}],
        results=[{"case_id": "case-a", "passed": True}],
    )

    assert report["report_status"] == "incomplete"
    assert report["summary"]["runner_case_status"] == "fail"
    assert report["summary"]["request_failure_family"] == "partial_report"


def test_founder_shard_report_is_not_final_gate() -> None:
    report = build_founder_report(
        "http://test",
        "2026-04-23",
        [{"case_id": "FR-001", "passed": True}],
        expected_total_cases=1,
        run_mode="shard",
    )

    assert report["report_status"] == "complete"
    assert report["summary"]["founder_gate"] == "fail"
    assert report["summary"]["final_gate_eligible"] is False
