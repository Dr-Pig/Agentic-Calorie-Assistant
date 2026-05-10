from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_manager_final_packet import (
    build_product_lab_manager_final_response_packet,
    product_lab_manager_final_packet_blockers,
)
from app.advanced_shadow_lab.product_lab_manager_tool_contract import (
    build_product_lab_manager_tool_registry,
    dormant_activation_fields,
)
from app.advanced_shadow_lab.product_lab_manager_tool_dispatch import (
    execute_product_lab_manager_tool_call,
)
from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore
from app.advanced_shadow_lab.product_lab_turn_policy import (
    LAB_MODE,
    base_turn,
    blocked_turn,
    turn_blockers,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract

SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_manager_tool_loop"
)

def run_product_lab_manager_tool_loop(
    *,
    lab_mode: str,
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    manager_script: list[Mapping[str, Any]],
    store: ProductLabMemoryStore | None = None,
) -> dict[str, Any]:
    guard_blockers = turn_blockers(lab_mode=lab_mode, turn=turn)
    if guard_blockers:
        return blocked_turn(turn=turn, lab_mode=lab_mode, blockers=guard_blockers)

    manager_passes, final_packet = _run_script(
        turn=turn,
        fixture_inputs=fixture_inputs,
        manager_script=manager_script,
        store=store,
    )
    tool_results = [
        result
        for manager_pass in manager_passes
        for result in manager_pass.get("tool_results") or []
        if isinstance(result, Mapping)
    ]
    blockers = [
        *_script_blockers(manager_script),
        *_tool_result_blockers(tool_results),
        *product_lab_manager_final_packet_blockers(
            final_packet,
            known_call_ids={str(result.get("call_id") or "") for result in tool_results},
            tool_call_count=len(tool_results),
        ),
    ]
    status = "blocked" if blockers else "pass"
    return {
        **base_turn(turn=turn, lab_mode=lab_mode),
        "artifact_type": "advanced_product_lab_manager_tool_loop_artifact",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_manager_tool_loop.py",
        "consumer": "advanced_product_lab_runtime_and_e2e_tests",
        "retirement_trigger": "approved_advanced_product_manager_runtime_activation",
        "lab_manager_tool_loop_enabled": lab_mode == LAB_MODE,
        "lab_runtime_connected": status == "pass",
        "lab_user_facing_behavior_changed": status == "pass",
        "raw_user_text_semantic_inference_performed": False,
        "manager_script_is_fixture_semantics": True,
        "manager_tool_registry": build_product_lab_manager_tool_registry(),
        "manager_pass_trace": manager_passes,
        "tool_result_trace": tool_results,
        "tool_call_count": len(tool_results),
        "dynamic_tool_results_returned_to_manager": bool(tool_results)
        and final_packet is not None
        and not blockers,
        "final_response_packet": final_packet or {},
        "product_capabilities_exercised": _capabilities(tool_results, blockers),
        **dormant_activation_fields(),
        "blockers": blockers,
        **dict(FALSE_FLAGS),
    }

def _run_script(
    *,
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    manager_script: list[Mapping[str, Any]],
    store: ProductLabMemoryStore | None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    prior_results: dict[str, dict[str, Any]] = {}
    manager_passes: list[dict[str, Any]] = []
    final_packet: dict[str, Any] | None = None
    for index, step in enumerate(manager_script):
        pass_trace, final_candidate = _run_step(
            index=index,
            step=step,
            turn=turn,
            fixture_inputs=fixture_inputs,
            store=store,
            prior_results=prior_results,
        )
        manager_passes.append(pass_trace)
        for result in pass_trace.get("tool_results") or []:
            if isinstance(result, Mapping) and result.get("call_id"):
                prior_results[str(result["call_id"])] = dict(result)
        if final_candidate is not None:
            final_packet = final_candidate
    return manager_passes, final_packet


def _run_step(
    *,
    index: int,
    step: Mapping[str, Any],
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    store: ProductLabMemoryStore | None,
    prior_results: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    action = str(step.get("action") or "")
    pass_id = str(step.get("pass_id") or f"manager-pass-{index + 1}")
    if action == "call_tools":
        results = [
            execute_product_lab_manager_tool_call(
                turn=turn,
                fixture_inputs=fixture_inputs,
                tool_call=call,
                store=store,
                prior_tool_results=prior_results,
            )
            for call in step.get("tool_calls") or []
            if isinstance(call, Mapping)
        ]
        return _pass_trace(pass_id, "call_tools", results), None
    if action == "final":
        packet = build_product_lab_manager_final_response_packet(
            _mapping(step.get("final_response")),
            prior_results,
        )
        return {
            "pass_id": pass_id,
            "manager_action": "final",
            "tool_call_count": 0,
            "tool_results_seen_count": len(prior_results),
            "final_response_packet": packet,
            "blockers": [],
        }, packet
    return _pass_trace(pass_id, action or "missing", []), None


def _pass_trace(pass_id: str, action: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    blockers = [] if action == "call_tools" else [f"manager_action.unsupported:{action}"]
    return {
        "pass_id": pass_id,
        "manager_action": action,
        "tool_call_count": len(results),
        "tool_results_returned_to_manager": action == "call_tools",
        "tool_results": results,
        "blockers": blockers,
    }


def _script_blockers(manager_script: list[Mapping[str, Any]]) -> list[str]:
    if not manager_script:
        return ["manager_script.missing"]
    return ["manager_script.too_many_passes"] if len(manager_script) > 6 else []


def _tool_result_blockers(tool_results: list[Mapping[str, Any]]) -> list[str]:
    return [
        f"{result.get('call_id') or 'unknown_call'}.{blocker}"
        for result in tool_results
        for blocker in result.get("blockers") or []
    ]


def _capabilities(tool_results: list[Mapping[str, Any]], blockers: list[str]) -> list[str]:
    if blockers:
        return []
    return sorted(
        str(result.get("capability_family") or "")
        for result in tool_results
        if result.get("status") == "pass" and result.get("capability_family")
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "run_product_lab_manager_tool_loop"]
