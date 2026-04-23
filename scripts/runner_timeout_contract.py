from __future__ import annotations

from typing import Any


def build_runner_timeout_contract(
    *,
    expected_total_cases: int,
    completed_cases: int,
    run_mode: str = "full",
    timed_out: bool = False,
    interrupted: bool = False,
) -> dict[str, Any]:
    expected = max(int(expected_total_cases or 0), 0)
    completed = max(int(completed_cases or 0), 0)
    full_integration = run_mode == "full"
    shard_run = run_mode == "shard"
    execution_complete = completed == expected and not timed_out and not interrupted
    report_status = "complete" if execution_complete else "incomplete"

    failure_family: str | None = None
    if timed_out:
        failure_family = "timeout"
    elif interrupted:
        failure_family = "interrupted"
    elif not execution_complete:
        failure_family = "partial_report"

    return {
        "report_status": report_status,
        "execution_complete": execution_complete,
        "expected_total_cases": expected,
        "completed_cases": completed,
        "full_integration": full_integration,
        "shard_run": shard_run,
        "final_gate_eligible": execution_complete and full_integration,
        "request_failure_family": failure_family,
    }


def apply_runner_timeout_contract(
    report: dict[str, Any],
    *,
    expected_total_cases: int,
    completed_cases: int,
    run_mode: str = "full",
    timed_out: bool = False,
    interrupted: bool = False,
    pass_fields: tuple[str, ...] = ("runner_case_status", "founder_gate", "bundle_gate"),
) -> dict[str, Any]:
    contract = build_runner_timeout_contract(
        expected_total_cases=expected_total_cases,
        completed_cases=completed_cases,
        run_mode=run_mode,
        timed_out=timed_out,
        interrupted=interrupted,
    )
    report.update(contract)
    report["runner_contract"] = dict(contract)
    summary = dict(report.get("summary") or {})
    summary.update(
        {
            "report_status": contract["report_status"],
            "execution_complete": contract["execution_complete"],
            "full_integration": contract["full_integration"],
            "shard_run": contract["shard_run"],
            "final_gate_eligible": contract["final_gate_eligible"],
            "request_failure_family": contract["request_failure_family"],
        }
    )
    if not contract["final_gate_eligible"]:
        for field in pass_fields:
            if summary.get(field) == "pass":
                summary[field] = "fail"
    report["summary"] = summary
    return report
