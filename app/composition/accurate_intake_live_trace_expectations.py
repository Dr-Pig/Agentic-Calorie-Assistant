from __future__ import annotations

from typing import Any

from app.composition.accurate_intake_live_trace_expectation_cases import (
    grade_case_trace_expectation,
)


def grade_live_trace_expectations(case: dict[str, Any]) -> dict[str, Any]:
    grade = grade_case_trace_expectation(case)
    if grade is not None:
        return grade
    case_id = str(case.get("case_id") or "")
    return {
        "expectation_id": "not_applicable",
        "case_id": case_id,
        "required_status": "not_applicable",
        "ideal_target_status": "not_applicable",
        "expected_trace": [],
        "checks": [],
        "ideal_targets": [],
    }


__all__ = ["grade_live_trace_expectations"]
