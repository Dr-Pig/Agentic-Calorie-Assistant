from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.capability_registry import build_shared_capability_registry


def order_capabilities(capabilities: list[str], ordering_constraints: list[str]) -> list[str]:
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


def planner_tool_arguments(capability_id: str) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "scope_keys": {
            "user_id": "lab-user",
            "workspace_id": "advanced-product-lab",
            "project_id": "advanced-product-lab",
            "surface": "chat",
        },
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "durable_product_memory_activation_allowed": False,
    }
    if capability_id == "intake":
        arguments["intake_manager_result"] = _intake_manager_result_stub()
    return arguments


def recommendation_turn_plan_projection(manager_turn_plan: Mapping[str, Any]) -> dict[str, Any]:
    requests = [
        request
        for request in manager_turn_plan.get("capability_requests") or []
        if isinstance(request, Mapping)
    ]
    return {
        "primary_workflow": str(manager_turn_plan.get("primary_workflow") or ""),
        "requested_capabilities": [
            {
                "capability_id": str(request.get("capability") or ""),
                "request_mode": "required",
                "priority": index,
            }
            for index, request in enumerate(requests, start=1)
        ],
        "candidate_tool_calls": [
            {
                "tool_name": str(request.get("tool_name") or ""),
                "capability_id": str(request.get("capability") or ""),
            }
            for request in requests
        ],
        "ordering_constraints": list(manager_turn_plan.get("ordering_constraints") or []),
        "response_obligations": ["recorded_vs_proposed_state_must_be_visible"],
    }


def tool_name_for_capability(capability_id: str) -> str:
    registry = build_shared_capability_registry()
    return {
        str(item["capability_id"]): str(item["shared_tool_name"])
        for item in registry["capabilities"]
    }[capability_id]


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _intake_manager_result_stub() -> dict[str, Any]:
    return {
        "artifact_type": "advanced_lab_intake_manager_result_contract_stub",
        "status": "available",
        "intent": "estimate_meal",
        "manager_action": "final",
        "final_action": "answer",
        "workflow_effect": "estimate",
        "answer_contract": {"estimated_kcal": 650},
        "tool_calls": [],
        "tool_results": [],
        "canonical_product_mutation_allowed": False,
    }


__all__ = [
    "mapping",
    "order_capabilities",
    "planner_tool_arguments",
    "recommendation_turn_plan_projection",
    "tool_name_for_capability",
]
