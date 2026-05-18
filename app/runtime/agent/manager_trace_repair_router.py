from __future__ import annotations

from typing import Any

from app.runtime.agent.manager_payload_utils import json_safe

MANAGER_TRACE_REPAIR_ROUTER_VERSION = "manager_trace_repair_router.v1"

TRACE_REPAIR_LAYER_ORDER = (
    "L1_prompt_architecture",
    "L2_context_packet",
    "L3_manager_semantics",
    "L4_tool_selection",
    "L5_evidence_packets",
    "L6_validator_guard",
    "L7_mutation_read_model",
    "L8_response",
    "L9_ui_same_truth",
)


def build_manager_trace_repair_router(
    *,
    manager_rounds: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    guard_outcome: dict[str, Any] | None,
    failure_family: str | None,
    requested_tools: list[str],
    executed_tools: list[str],
) -> dict[str, Any]:
    first_round = manager_rounds[0] if manager_rounds else {}
    final_round = manager_rounds[-1] if manager_rounds else {}
    final_decision = dict(final_round.get("decision") or {}) if isinstance(final_round, dict) else {}
    semantic_decision = dict(final_decision.get("semantic_decision") or {})
    active_resolution = semantic_decision.get("active_workflow_resolution")
    prompt_layer_contract = dict(first_round.get("prompt_layer_contract") or {}) if isinstance(first_round, dict) else {}
    phase_a_input = dict(final_round.get("phase_a_input") or {}) if isinstance(final_round, dict) else {}
    evidence_failures = _tool_result_failure_families(tool_results)
    guard_failure = str((guard_outcome or {}).get("failure_family") or "")

    layers = {
        "L1_prompt_architecture": {
            "present": bool(prompt_layer_contract),
            "evidence": {
                "prompt_layer_contract_version": prompt_layer_contract.get("contract_version"),
                "uncategorized_dynamic_keys": (
                    (prompt_layer_contract.get("runtime_payload_layer_plan") or {}).get("uncategorized_dynamic_keys")
                    if isinstance(prompt_layer_contract.get("runtime_payload_layer_plan"), dict)
                    else None
                ),
            },
        },
        "L2_context_packet": {
            "present": isinstance(phase_a_input.get("manager_context_packet_v1"), dict),
            "evidence": {
                "context_packet_present": isinstance(phase_a_input.get("manager_context_packet_v1"), dict),
                "manager_loop_scope": phase_a_input.get("manager_loop_scope"),
            },
        },
        "L3_manager_semantics": {
            "present": bool(semantic_decision),
            "evidence": {
                "active_workflow_resolution_present": isinstance(active_resolution, dict),
                "manager_action": final_decision.get("manager_action"),
                "final_action": final_decision.get("final_action"),
                "workflow_effect": final_decision.get("workflow_effect"),
            },
        },
        "L4_tool_selection": {
            "present": bool(requested_tools or executed_tools),
            "evidence": {
                "requested_tools": list(requested_tools),
                "executed_tools": list(executed_tools),
            },
        },
        "L5_evidence_packets": {
            "present": bool(tool_results),
            "evidence": {
                "tool_result_count": len(tool_results),
                "tool_failure_families": evidence_failures,
            },
        },
        "L6_validator_guard": {
            "present": bool(guard_outcome) or bool(failure_family),
            "evidence": {
                "guard_failure_family": guard_failure or None,
                "request_failure_family": failure_family,
            },
        },
        "L7_mutation_read_model": {
            "present": "mutation" in str(final_decision.get("workflow_effect") or "").lower()
            or str(final_decision.get("final_action") or "") in {"commit", "correction_applied", "record_observation"},
            "evidence": {
                "final_action": final_decision.get("final_action"),
                "workflow_effect": final_decision.get("workflow_effect"),
            },
        },
        "L8_response": {
            "present": isinstance(final_decision.get("answer_contract"), dict),
            "evidence": {
                "answer_contract_present": isinstance(final_decision.get("answer_contract"), dict),
            },
        },
        "L9_ui_same_truth": {
            "present": isinstance(final_decision.get("ui_same_truth"), dict)
            or isinstance(final_decision.get("renderer_input_basis"), dict),
            "evidence": {
                "ui_same_truth_trace_present": isinstance(final_decision.get("ui_same_truth"), dict),
                "renderer_input_basis_present": isinstance(final_decision.get("renderer_input_basis"), dict),
            },
        },
    }
    primary_layer = _primary_repair_layer(
        layers=layers,
        failure_family=str(failure_family or guard_failure or ""),
        evidence_failures=evidence_failures,
    )
    return {
        "router_version": MANAGER_TRACE_REPAIR_ROUTER_VERSION,
        "claim_scope": "diagnostic_layer_attribution_not_product_truth",
        "semantic_owner": "manager",
        "deterministic_role": "trace_attribution_only_no_semantic_rewrite",
        "layer_order": list(TRACE_REPAIR_LAYER_ORDER),
        "layers": json_safe(layers),
        "primary_repair_layer": primary_layer,
        "blocking_failure_family": str(failure_family or guard_failure or "") or None,
    }


def _tool_result_failure_families(tool_results: list[dict[str, Any]]) -> list[str]:
    families: list[str] = []
    for result in tool_results:
        if not isinstance(result, dict):
            continue
        family = str(result.get("failure_family") or "").strip()
        if family and family not in families:
            families.append(family)
    return families


def _primary_repair_layer(
    *,
    layers: dict[str, dict[str, Any]],
    failure_family: str,
    evidence_failures: list[str],
) -> str | None:
    if failure_family in {"manager_output_contract_violation", "final_payload_shape_error"}:
        return "L1_prompt_architecture"
    if not bool((layers["L3_manager_semantics"]["evidence"] or {}).get("active_workflow_resolution_present")):
        return "L3_manager_semantics"
    if any("tool" in family for family in evidence_failures) or failure_family in {"tool_routing_gap", "tool_scope_violation"}:
        return "L4_tool_selection"
    if failure_family in {"commit_without_evidence", "nutrition_evidence_unavailable"}:
        return "L5_evidence_packets"
    if failure_family in {"ui_same_truth_mismatch", "renderer_read_model_mismatch"}:
        return "L9_ui_same_truth"
    if failure_family:
        return "L6_validator_guard"
    return None


__all__ = [
    "MANAGER_TRACE_REPAIR_ROUTER_VERSION",
    "TRACE_REPAIR_LAYER_ORDER",
    "build_manager_trace_repair_router",
]
