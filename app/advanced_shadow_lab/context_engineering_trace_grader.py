from __future__ import annotations

from typing import Any, Mapping


def grade_context_engineering_trace(trace: Mapping[str, Any]) -> dict[str, Any]:
    checks = {
        "capabilities_considered_visible": bool(trace.get("capabilities_considered")),
        "capabilities_invoked_visible": bool(trace.get("capabilities_invoked")),
        "capabilities_omitted_visible": "capabilities_omitted" in trace,
        "blocked_tools_visible": "blocked_tools" in trace,
        "response_claim_boundary_visible": bool(trace.get("response_claim_boundary")),
    }
    blockers = [
        check_name
        for check_name, passed in checks.items()
        if passed is not True
    ]
    return {
        "artifact_type": "advanced_product_lab_context_engineering_trace_grade",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "checks": checks,
        "blockers": blockers,
    }


def grade_manager_turn_plan_for_case(
    case: Mapping[str, Any],
    manager_turn_plan: Mapping[str, Any],
) -> dict[str, Any]:
    requests = _capability_requests(manager_turn_plan)
    invoked = [str(request.get("capability") or "") for request in requests]
    blockers = [
        *_required_capability_blockers(case, invoked),
        *_forbidden_capability_blockers(case, invoked),
        *_ordering_blockers(case, invoked),
        *_argument_blockers(requests),
        *_mutation_blockers(case, manager_turn_plan),
        *_final_boundary_blockers(manager_turn_plan),
    ]
    checked_ordering = [str(item) for item in case.get("expected_ordering_constraints") or []]
    return {
        "artifact_type": "advanced_product_lab_manager_turn_plan_grade",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "case_id": str(case.get("case_id") or manager_turn_plan.get("case_id") or ""),
        "required_capability_count": len(_strings(case.get("expected_capabilities"))),
        "forbidden_capability_count": len(
            set(invoked).intersection(_strings(case.get("forbidden_capabilities")))
        ),
        "ordering_constraints_checked": checked_ordering,
        "capabilities_invoked": invoked,
        "blockers": blockers,
        "raw_user_text_semantic_inference_performed": False,
        "canonical_product_mutation_allowed": False,
        "scheduler_delivery_allowed": False,
    }


def _required_capability_blockers(
    case: Mapping[str, Any],
    invoked: list[str],
) -> list[str]:
    return [
        f"required_capability.missing:{capability}"
        for capability in _strings(case.get("expected_capabilities"))
        if capability not in invoked
    ]


def _forbidden_capability_blockers(
    case: Mapping[str, Any],
    invoked: list[str],
) -> list[str]:
    forbidden = set(_strings(case.get("forbidden_capabilities")))
    return [
        f"forbidden_capability.invoked:{capability}"
        for capability in invoked
        if capability in forbidden
    ]


def _ordering_blockers(
    case: Mapping[str, Any],
    invoked: list[str],
) -> list[str]:
    blockers: list[str] = []
    for constraint in _strings(case.get("expected_ordering_constraints")):
        if "_before_" not in constraint:
            continue
        before, after = constraint.split("_before_", 1)
        if before in invoked and after in invoked and invoked.index(before) > invoked.index(after):
            blockers.append(f"ordering.{constraint}.violated")
    return blockers


def _argument_blockers(requests: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for request in requests:
        capability = str(request.get("capability") or "")
        tool_name = str(request.get("tool_name") or "")
        arguments = _mapping(request.get("arguments"))
        if not tool_name:
            blockers.append(f"{capability or 'unknown'}.tool_name.missing")
        if capability == "intake" and not isinstance(
            arguments.get("intake_manager_result"), Mapping
        ):
            blockers.append("intake.arguments.intake_manager_result_missing")
    return blockers


def _mutation_blockers(
    case: Mapping[str, Any],
    manager_turn_plan: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    expected = str(case.get("mutation_posture") or "")
    actual = str(manager_turn_plan.get("mutation_posture") or "")
    if expected and actual != expected:
        blockers.append(f"mutation_posture.expected_{expected}_actual_{actual}")
    if manager_turn_plan.get("canonical_product_mutation_allowed") is True:
        blockers.append("canonical_product_mutation_allowed_true")
    return blockers


def _final_boundary_blockers(manager_turn_plan: Mapping[str, Any]) -> list[str]:
    return [] if manager_turn_plan.get("final_response_boundary") else [
        "final_response_boundary.missing"
    ]


def _capability_requests(manager_turn_plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        item
        for item in manager_turn_plan.get("capability_requests") or []
        if isinstance(item, Mapping)
    ]


def _strings(value: object) -> list[str]:
    return [str(item) for item in value or [] if str(item)]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["grade_context_engineering_trace", "grade_manager_turn_plan_for_case"]
