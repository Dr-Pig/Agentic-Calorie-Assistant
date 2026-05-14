from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.context_engineering_case_loader import (
    load_context_engineering_golden_set,
)
from app.advanced_shadow_lab.context_engineering_fixture_turn_plan_provider import (
    FixtureContextEngineeringTurnPlanProvider,
)


def build_context_engineering_holdout_gate() -> dict[str, Any]:
    provider = FixtureContextEngineeringTurnPlanProvider(model_profile="fixture-manager")
    cases = [
        case
        for case in load_context_engineering_golden_set()["cases"]
        if case.get("split") == "negative_holdout"
    ]
    case_reports = [_case_report(case, provider.plan_case(case)) for case in cases]
    blockers = [
        blocker
        for report in case_reports
        for blocker in report.get("blockers", [])
    ]
    return {
        "artifact_type": "advanced_product_lab_ce_stress_holdout_report",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "negative_holdout_case_count": len(case_reports),
        "overtrigger_violation_count": _count_blockers(case_reports, "forbidden_capability"),
        "undertrigger_violation_count": _count_blockers(case_reports, "required_capability"),
        "prompt_injection_case_ids": [
            str(case["case_id"])
            for case in cases
            if "scheduler_delivery" in case.get("forbidden_capabilities", [])
            and "canonical_mutation" in case.get("forbidden_capabilities", [])
        ],
        "cases": case_reports,
        "raw_user_text_semantic_inference_performed": False,
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
        "scheduler_delivery_allowed": False,
        "blockers": blockers,
    }


def holdout_case_blockers(case: Mapping[str, Any], invoked_capabilities: list[str]) -> list[str]:
    case_id = str(case.get("case_id") or "unknown")
    required = [str(item) for item in case.get("expected_capabilities") or []]
    forbidden = {str(item) for item in case.get("forbidden_capabilities") or []}
    blockers = [
        f"{case_id}.required_capability.missing:{capability}"
        for capability in required
        if capability not in invoked_capabilities
    ]
    blockers.extend(
        f"{case_id}.forbidden_capability.invoked:{capability}"
        for capability in invoked_capabilities
        if capability in forbidden
    )
    return blockers


def _case_report(
    case: Mapping[str, Any],
    planner_trace: Mapping[str, Any],
) -> dict[str, Any]:
    invoked = [
        str(request.get("capability") or "")
        for request in _manager_plan_requests(planner_trace)
    ]
    blockers = [
        *holdout_case_blockers(case, invoked),
        *[
            f"{case.get('case_id')}.planner.{blocker}"
            for blocker in planner_trace.get("blockers") or []
        ],
    ]
    return {
        "case_id": str(case.get("case_id") or ""),
        "status": "pass" if not blockers else "blocked",
        "invoked_capabilities": invoked,
        "forbidden_capabilities": [str(item) for item in case.get("forbidden_capabilities") or []],
        "no_op_answer": not invoked,
        "raw_user_text_semantic_inference_performed": False,
        "blockers": blockers,
    }


def _manager_plan_requests(planner_trace: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    plan = planner_trace.get("manager_turn_plan")
    if not isinstance(plan, Mapping):
        return []
    return [
        request
        for request in plan.get("capability_requests") or []
        if isinstance(request, Mapping)
    ]


def _count_blockers(case_reports: list[Mapping[str, Any]], family: str) -> int:
    return sum(
        1
        for report in case_reports
        for blocker in report.get("blockers") or []
        if f".{family}." in str(blocker)
    )


__all__ = ["build_context_engineering_holdout_gate", "holdout_case_blockers"]
