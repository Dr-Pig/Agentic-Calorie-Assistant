from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.context_engineering_case_loader import (
    load_context_engineering_golden_set,
)
from app.shared.contracts.capability_registry import build_shared_capability_registry
from app.shared.contracts.tool_choice_walls import validate_tool_choice_walls


def build_context_engineering_tool_choice_wall_trace(
    *, case_ids: list[str] | None = None
) -> dict[str, Any]:
    golden_set = load_context_engineering_golden_set()
    requested_ids = set(case_ids or [])
    selected_cases = [
        case
        for case in golden_set["cases"]
        if not requested_ids or str(case["case_id"]) in requested_ids
    ]

    case_traces = [_build_case_trace(case) for case in selected_cases]
    blockers = [
        blocker
        for case_trace in case_traces
        for blocker in case_trace.get("blockers", [])
    ]
    return {
        "artifact_type": "advanced_product_lab_tool_choice_wall_trace",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "fail",
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        "canonical_mutation_allowed": False,
        "durable_product_memory_activation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "case_count": len(case_traces),
        "cases": case_traces,
        "blockers": blockers,
    }


def _build_case_trace(case: Mapping[str, Any]) -> dict[str, Any]:
    capabilities = [str(item) for item in case.get("expected_capabilities") or []]
    ordering_constraints = [
        str(item) for item in case.get("expected_ordering_constraints") or []
    ]
    ordered_capabilities = _order_capabilities(capabilities, ordering_constraints)
    tool_calls = [_tool_call(capability_id) for capability_id in ordered_capabilities]
    validation = validate_tool_choice_walls(
        requested_capability_ids=capabilities,
        tool_calls=tool_calls,
        ordering_constraints=ordering_constraints,
    )
    return {
        "case_id": str(case["case_id"]),
        "status": validation["status"],
        "expected_capabilities": capabilities,
        "tool_order": validation["tool_order"],
        "ordering_constraints_checked": validation["ordering_constraints_checked"],
        "mutation_guard_checked": validation["mutation_guard_checked"],
        "blockers": validation["blockers"],
    }


def _order_capabilities(capabilities: list[str], ordering_constraints: list[str]) -> list[str]:
    remaining = list(dict.fromkeys(capabilities))
    edges: dict[str, set[str]] = {capability: set() for capability in remaining}
    indegree = {capability: 0 for capability in remaining}
    for constraint in ordering_constraints:
        if "_before_" not in constraint:
            continue
        first, second = constraint.split("_before_", 1)
        if first in edges and second in edges and second not in edges[first]:
            edges[first].add(second)
            indegree[second] += 1

    ordered: list[str] = []
    while remaining:
        next_capability = next(
            (capability for capability in remaining if indegree[capability] == 0),
            remaining[0],
        )
        remaining.remove(next_capability)
        ordered.append(next_capability)
        for child in edges[next_capability]:
            indegree[child] -= 1
    return ordered


def _tool_call(capability_id: str) -> dict[str, Any]:
    registry = build_shared_capability_registry()
    tool_by_capability = {
        str(item["capability_id"]): str(item["shared_tool_name"])
        for item in registry["capabilities"]
    }
    return {
        "tool_name": tool_by_capability[capability_id],
        "capability_id": capability_id,
        "arguments": {
            "lab_enabled": True,
            "mainline_activation_enabled": False,
            "canonical_product_mutation_allowed": False,
            "production_scheduler_delivery_allowed": False,
            "durable_product_memory_activation_allowed": False,
        },
    }


__all__ = ["build_context_engineering_tool_choice_wall_trace"]
