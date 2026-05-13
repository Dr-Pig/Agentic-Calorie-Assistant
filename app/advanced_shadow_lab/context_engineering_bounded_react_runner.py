from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.context_engineering_case_loader import (
    load_context_engineering_golden_set,
)
from app.advanced_shadow_lab.context_engineering_fixture_planner_provider import (
    FixtureContextEngineeringPlannerProvider,
)
from app.advanced_shadow_lab.context_engineering_fixture_planner_support import (
    mapping,
    recommendation_turn_plan_projection,
)
from app.advanced_shadow_lab.product_lab_manager_tool_dispatch import (
    execute_product_lab_manager_tool_call,
)
from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore


CONTEXT_CAPABILITIES = {"intake", "query", "memory", "reusable_meal", "pending_meal_intent"}


def run_context_engineering_bounded_react_trace(
    *,
    case_id: str,
    fixture_inputs: Mapping[str, Any],
    max_manager_passes: int = 2,
    store: ProductLabMemoryStore | None = None,
) -> dict[str, Any]:
    if max_manager_passes < 2:
        return _blocked(case_id, ["react_pass_budget.too_low_for_replan"])
    case = _case(case_id)
    planner_trace = FixtureContextEngineeringPlannerProvider(
        model_profile="fixture-manager"
    ).plan_case(case)
    if planner_trace["status"] != "pass":
        return _blocked(
            case_id,
            [f"planner.{blocker}" for blocker in planner_trace.get("blockers") or []],
        )

    requests = [
        request
        for request in planner_trace["manager_turn_plan"]["capability_requests"]
        if isinstance(request, Mapping)
    ]
    context_requests = [
        request for request in requests if request.get("capability") in CONTEXT_CAPABILITIES
    ]
    downstream_requests = [
        request for request in requests if request.get("capability") not in CONTEXT_CAPABILITIES
    ]
    prior_results: dict[str, dict[str, Any]] = {}
    first_pass = _execute_pass(
        pass_id="manager-pass-1",
        action="call_tools",
        requests=context_requests,
        prior_results=prior_results,
        fixture_inputs=fixture_inputs,
        store=store,
    )
    _remember_results(prior_results, first_pass)
    second_pass = _execute_pass(
        pass_id="manager-pass-2",
        action="replan_after_tool_results",
        requests=downstream_requests,
        prior_results=prior_results,
        fixture_inputs=fixture_inputs,
        store=store,
        manager_turn_plan=planner_trace["manager_turn_plan"],
    )
    _remember_results(prior_results, second_pass)
    passes = [first_pass, second_pass]
    blockers = [
        f"{result.get('call_id')}.{blocker}"
        for manager_pass in passes
        for result in manager_pass.get("tool_results") or []
        if isinstance(result, Mapping)
        for blocker in result.get("blockers") or []
    ]
    return {
        "artifact_type": "advanced_product_lab_bounded_react_replan_trace",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "case_id": case_id,
        "semantic_decision_owner": "fixture_provider_manager_turn_plan",
        "deterministic_replan_role": "partition_validate_and_execute",
        "deterministic_semantic_rewrite_performed": False,
        "manager_pass_count": len(passes),
        "manager_pass_trace": passes,
        "tool_result_count": sum(len(item["tool_results"]) for item in passes),
        "final_response_deferred_to_slice13": True,
        "raw_user_text_semantic_inference_performed": False,
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
        "blockers": blockers,
    }


def _execute_pass(
    *,
    pass_id: str,
    action: str,
    requests: list[Mapping[str, Any]],
    prior_results: Mapping[str, Mapping[str, Any]],
    fixture_inputs: Mapping[str, Any],
    store: ProductLabMemoryStore | None,
    manager_turn_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    results = [
        execute_product_lab_manager_tool_call(
            turn=_turn(),
            fixture_inputs=fixture_inputs,
            tool_call={
                "call_id": _call_id(request, index),
                "tool_name": str(request.get("tool_name") or ""),
                "arguments": _arguments(request, manager_turn_plan),
            },
            store=store,
            prior_tool_results=prior_results,
        )
        for index, request in enumerate(requests, start=1)
    ]
    return {
        "pass_id": pass_id,
        "manager_action": action,
        "tool_results_seen_count": len(prior_results),
        "tool_order": [str(request.get("tool_name") or "") for request in requests],
        "tool_results_returned_to_manager": True,
        "tool_results": results,
    }


def _arguments(
    request: Mapping[str, Any],
    manager_turn_plan: Mapping[str, Any] | None,
) -> dict[str, Any]:
    arguments = dict(_mapping(request.get("arguments")))
    if request.get("tool_name") == "recommendation.run" and manager_turn_plan:
        arguments["manager_turn_plan"] = recommendation_turn_plan_projection(manager_turn_plan)
    return arguments


def _case(case_id: str) -> Mapping[str, Any]:
    for case in load_context_engineering_golden_set()["cases"]:
        if str(case.get("case_id") or "") == case_id:
            return case
    raise ValueError(f"unknown context engineering case: {case_id}")


def _call_id(request: Mapping[str, Any], index: int) -> str:
    capability = str(request.get("capability") or "tool").replace("_", "-")
    return f"{capability}-{index}"


def _remember_results(
    prior_results: dict[str, dict[str, Any]],
    pass_trace: Mapping[str, Any],
) -> None:
    for result in pass_trace.get("tool_results") or []:
        if isinstance(result, Mapping) and result.get("call_id"):
            prior_results[str(result["call_id"])] = dict(result)


def _blocked(case_id: str, blockers: list[str]) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_bounded_react_replan_trace",
        "artifact_schema_version": "1.0",
        "status": "blocked",
        "case_id": case_id,
        "manager_pass_trace": [],
        "blockers": blockers,
    }


def _turn() -> dict[str, Any]:
    return {"session_id": "ce-react-session", "turn_id": "ce-react-turn", "surface": "chat"}


def _mapping(value: Any) -> Mapping[str, Any]:
    return mapping(value)


__all__ = ["run_context_engineering_bounded_react_trace"]
