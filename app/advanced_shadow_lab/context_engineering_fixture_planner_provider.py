from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.context_engineering_case_loader import (
    load_context_engineering_golden_set,
)
from app.advanced_shadow_lab.context_engineering_trace_grader import (
    grade_manager_turn_plan_for_case,
)
from app.shared.contracts.capability_registry import build_shared_capability_registry
from app.shared.contracts.tool_choice_walls import validate_tool_choice_walls


FORBIDDEN_PLANNER_FIELDS = {
    "keyword_route",
    "messages",
    "prompt",
    "raw_transcript",
    "raw_user_input",
    "raw_user_text",
    "user_turn",
}


class FixtureContextEngineeringPlannerProvider:
    provider_name = "fixture_context_engineering_manager_planner"

    def __init__(self, *, model_profile: str) -> None:
        self.model_profile = model_profile

    def plan_case(self, case: Mapping[str, Any]) -> dict[str, Any]:
        capabilities = [str(item) for item in case.get("expected_capabilities") or []]
        ordering = [str(item) for item in case.get("expected_ordering_constraints") or []]
        ordered_capabilities = _order_capabilities(capabilities, ordering)
        plan = _manager_turn_plan(case, ordered_capabilities, ordering)
        tool_calls = [
            {
                "tool_name": request["tool_name"],
                "capability_id": request["capability"],
                "arguments": request["arguments"],
            }
            for request in plan["capability_requests"]
        ]
        artifact = {
            "artifact_type": "advanced_product_lab_fixture_planner_trace",
            "artifact_schema_version": "1.0",
            "status": "pass",
            "provider_mode": "fixture_provider_contract",
            "owner": "manager_llm_fixture_provider",
            "model_profile": self.model_profile,
            "case_id": str(case.get("case_id") or ""),
            "manager_turn_plan": plan,
            "tool_choice_validation": validate_tool_choice_walls(
                requested_capability_ids=capabilities,
                tool_calls=tool_calls,
                ordering_constraints=ordering,
            ),
            "manager_turn_plan_grade": grade_manager_turn_plan_for_case(case, plan),
            "raw_user_text_semantic_inference_performed": False,
            "case_user_turn_included": False,
            "mainline_activation_enabled": False,
            "canonical_product_mutation_allowed": False,
        }
        artifact["blockers"] = fixture_planner_output_blockers(artifact)
        if artifact["blockers"]:
            artifact["status"] = "blocked"
        return artifact


def build_context_engineering_fixture_planner_trace(
    *, case_ids: list[str] | None = None
) -> dict[str, Any]:
    provider = FixtureContextEngineeringPlannerProvider(model_profile="fixture-manager")
    golden_set = load_context_engineering_golden_set()
    requested_ids = set(case_ids or [])
    selected_cases = [
        case
        for case in golden_set["cases"]
        if not requested_ids or str(case["case_id"]) in requested_ids
    ]
    case_traces = [provider.plan_case(case) for case in selected_cases]
    blockers = [
        blocker
        for trace in case_traces
        for blocker in trace.get("blockers", [])
    ]
    return {
        "artifact_type": "advanced_product_lab_fixture_planner_suite_trace",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "case_count": len(case_traces),
        "cases": case_traces,
        "provider_mode": "fixture_provider_contract",
        "raw_user_text_semantic_inference_performed": False,
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
        "blockers": blockers,
    }


def fixture_planner_output_blockers(artifact: Mapping[str, Any]) -> list[str]:
    blockers = [
        f"planner_output.forbidden_field:{field}"
        for field in sorted(FORBIDDEN_PLANNER_FIELDS)
        if field in artifact
    ]
    plan = artifact.get("manager_turn_plan")
    if isinstance(plan, Mapping) and plan.get("canonical_product_mutation_allowed") is True:
        blockers.append("manager_turn_plan.canonical_product_mutation_allowed_true")
    for key in ("tool_choice_validation", "manager_turn_plan_grade"):
        nested = artifact.get(key)
        if isinstance(nested, Mapping) and nested.get("status") not in {"pass", None}:
            blockers.extend(f"{key}.{blocker}" for blocker in nested.get("blockers") or [])
    return blockers


def _manager_turn_plan(
    case: Mapping[str, Any],
    capabilities: list[str],
    ordering: list[str],
) -> dict[str, Any]:
    final_boundary = _mapping(case.get("expected_trace")).get("final_response_boundary")
    return {
        "case_id": str(case.get("case_id") or ""),
        "primary_workflow": str(case.get("expected_primary_workflow") or ""),
        "capability_requests": [
            {
                "capability": capability,
                "tool_name": _tool_name(capability),
                "arguments": _tool_arguments(capability),
            }
            for capability in capabilities
        ],
        "ordering_constraints": ordering,
        "mutation_posture": str(case.get("mutation_posture") or ""),
        "final_response_boundary": str(final_boundary or "recorded_vs_proposed_state_must_be_visible"),
        "canonical_product_mutation_allowed": False,
        "scheduler_delivery_allowed": False,
        "raw_user_text_semantic_inference_performed": False,
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


def _tool_name(capability_id: str) -> str:
    registry = build_shared_capability_registry()
    return {
        str(item["capability_id"]): str(item["shared_tool_name"])
        for item in registry["capabilities"]
    }[capability_id]


def _tool_arguments(capability_id: str) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "durable_product_memory_activation_allowed": False,
    }
    if capability_id == "intake":
        arguments["intake_manager_result"] = {
            "artifact_type": "advanced_lab_intake_manager_result_contract_stub",
            "status": "available",
            "canonical_product_mutation_allowed": False,
        }
    return arguments


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "FixtureContextEngineeringPlannerProvider",
    "build_context_engineering_fixture_planner_trace",
    "fixture_planner_output_blockers",
]
