from __future__ import annotations

from typing import Any, Mapping


def grade_memory_record_grokfast_extraction(
    *,
    cases: list[Mapping[str, Any]],
    provider_result: Mapping[str, Any],
) -> dict[str, Any]:
    results_by_id = {
        str(result.get("case_id") or ""): result
        for result in provider_result.get("case_results") or []
        if isinstance(result, Mapping)
    }
    case_reports = [
        _grade_case(case=case, result=results_by_id.get(str(case.get("case_id") or "")))
        for case in cases
    ]
    blockers = [
        blocker
        for report in case_reports
        for blocker in report["blockers"]
    ]
    return {
        "case_reports": case_reports,
        "summary": {
            "case_count": len(cases),
            "passed_case_count": len([report for report in case_reports if not report["blockers"]]),
            "failed_case_count": len([report for report in case_reports if report["blockers"]]),
        },
        "blockers": blockers,
    }


def _grade_case(
    *,
    case: Mapping[str, Any],
    result: Mapping[str, Any] | None,
) -> dict[str, Any]:
    case_id = str(case.get("case_id") or "")
    if result is None:
        return {"case_id": case_id, "blockers": [f"case:{case_id}.missing_result"]}
    expected = _mapping(case.get("expected_candidate"))
    blockers: list[str] = []
    _expect_equal(blockers, case_id, "candidate_type", expected, result)
    _expect_optional_equal(blockers, case_id, "polarity", expected, result)
    _expect_optional_equal(blockers, case_id, "strength", expected, result)
    if expected.get("promotion_allowed_now") is False and result.get("promotion_allowed_now") is True:
        blockers.append(f"case:{case_id}.promotion_allowed_now_mismatch")
    if expected.get("human_review_required") is True and result.get("human_review_required") is not True:
        blockers.append(f"case:{case_id}.human_review_required_mismatch")
    if expected.get("candidate_type") != "none" and not result.get("source_refs"):
        blockers.append(f"case:{case_id}.source_refs_missing")
    return {
        "case_id": case_id,
        "candidate_type": str(result.get("candidate_type") or ""),
        "polarity": str(result.get("polarity") or ""),
        "strength": str(result.get("strength") or ""),
        "blockers": blockers,
    }


def _expect_equal(
    blockers: list[str],
    case_id: str,
    field: str,
    expected: Mapping[str, Any],
    result: Mapping[str, Any],
) -> None:
    if str(expected.get(field) or "") != str(result.get(field) or ""):
        blockers.append(f"case:{case_id}.{field}_mismatch")


def _expect_optional_equal(
    blockers: list[str],
    case_id: str,
    field: str,
    expected: Mapping[str, Any],
    result: Mapping[str, Any],
) -> None:
    expected_value = str(expected.get(field) or "")
    if expected_value and expected_value != str(result.get(field) or ""):
        blockers.append(f"case:{case_id}.{field}_mismatch")


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
