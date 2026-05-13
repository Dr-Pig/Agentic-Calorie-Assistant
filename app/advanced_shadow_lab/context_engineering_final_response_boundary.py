from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.context_engineering_bounded_react_runner import (
    run_context_engineering_bounded_react_trace,
)
from app.advanced_shadow_lab.product_lab_manager_final_packet import (
    build_product_lab_manager_final_response_packet,
)
from app.shared.contracts.manager_tool_result_envelope import normalize_manager_tool_result


RECORDED_FACT_CAPABILITIES = {"intake", "query"}
PROPOSAL_CAPABILITIES = {"recommendation", "rescue", "proactive"}
PENDING_CONTEXT_CAPABILITIES = {"pending_meal_intent", "memory", "reusable_meal"}
MUST_NOT_CLAIM = [
    "logged_when_not_committed",
    "scheduled_when_not_sent",
    "mutated_when_guard_not_passed",
    "budget_changed_until_acceptance",
    "meal_logged_until_commit",
]


def build_context_engineering_final_response_boundary_grade(
    *,
    case_id: str,
    fixture_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    react_trace = run_context_engineering_bounded_react_trace(
        case_id=case_id,
        fixture_inputs=fixture_inputs,
    )
    tool_results = _tool_results(react_trace)
    prior_results = {str(result["call_id"]): result for result in tool_results}
    final_packet = build_product_lab_manager_final_response_packet(
        {
            "copy": "Lab chat synthesis with visible claim boundaries.",
            "source_tool_call_ids": list(prior_results),
            "response_mode": "chat_first",
        },
        prior_results,
    )
    capabilities = _capabilities(tool_results)
    grade = {
        "artifact_type": "advanced_product_lab_final_response_boundary_grade",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "case_id": case_id,
        "final_response_packet": final_packet,
        "recorded_fact_capabilities": _filter(capabilities, RECORDED_FACT_CAPABILITIES),
        "proposal_capabilities": _filter(capabilities, PROPOSAL_CAPABILITIES),
        "pending_context_capabilities": _filter(capabilities, PENDING_CONTEXT_CAPABILITIES),
        "no_op_answer": not capabilities,
        "must_not_claim": list(MUST_NOT_CLAIM),
        "tool_names_exposed_to_user": False,
        "served_to_mainline_user": False,
        "canonical_product_mutation_allowed": False,
        "blockers": [],
    }
    grade["blockers"] = final_response_boundary_blockers(grade)
    if react_trace.get("status") != "pass":
        grade["blockers"].extend(f"react.{blocker}" for blocker in react_trace["blockers"])
    if grade["blockers"]:
        grade["status"] = "blocked"
    return grade


def final_response_boundary_blockers(packet: Mapping[str, Any]) -> list[str]:
    claim_flags = _mapping(packet.get("claim_flags"))
    blockers = [
        f"final_response.claim_forbidden:{claim}"
        for claim in MUST_NOT_CLAIM
        if claim_flags.get(claim) is True
    ]
    if packet.get("tool_names_exposed_to_user") is True:
        blockers.append("final_response.tool_names_exposed_to_user")
    if packet.get("served_to_mainline_user") is True:
        blockers.append("final_response.served_to_mainline_user")
    if packet.get("canonical_product_mutation_allowed") is True:
        blockers.append("final_response.canonical_product_mutation_allowed")
    return blockers


def _tool_results(react_trace: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        result
        for manager_pass in react_trace.get("manager_pass_trace") or []
        for result in manager_pass.get("tool_results") or []
        if isinstance(result, Mapping)
    ]


def _capabilities(tool_results: list[Mapping[str, Any]]) -> list[str]:
    capabilities: list[str] = []
    seen: set[str] = set()
    for result in tool_results:
        normalized = _mapping(result.get("normalized_result_envelope"))
        if not normalized:
            normalized = normalize_manager_tool_result(result)
        capability = str(normalized.get("capability_id") or "")
        if capability and capability != "unknown" and capability not in seen:
            seen.add(capability)
            capabilities.append(capability)
    return capabilities


def _filter(capabilities: list[str], allowed: set[str]) -> list[str]:
    return [capability for capability in capabilities if capability in allowed]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "build_context_engineering_final_response_boundary_grade",
    "final_response_boundary_blockers",
]
