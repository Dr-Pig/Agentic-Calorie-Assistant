from __future__ import annotations

from typing import Any, Mapping


EXPECTED_TOOL_ORDER = ["memory.search", "reusable_meal.search", "rescue.run"]


def manager_turn_runtime_blockers(runtime_artifact: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if runtime_artifact.get("artifact_type") != "advanced_product_lab_turn_artifact":
        blockers.append("runtime.unsupported_artifact_type")
    if runtime_artifact.get("status") != "pass":
        blockers.append("runtime.status_not_pass")
    if manager_turn_tool_order(runtime_artifact) != EXPECTED_TOOL_ORDER:
        blockers.append("runtime.manager_tool_order_mismatch")
    for flag in (
        "mainline_runtime_connected",
        "canonical_product_mutation_allowed",
        "durable_product_memory_written",
        "manager_context_packet_changed",
    ):
        if runtime_artifact.get(flag) is True:
            blockers.append(f"runtime.{flag}")
    return blockers


def manager_turn_output_guard(output: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if str(output.get("claim_scope") or "") != "diagnostic_only":
        blockers.append("output.claim_scope_not_diagnostic_only")
    if [str(item) for item in output.get("tool_call_order") or []] != EXPECTED_TOOL_ORDER:
        blockers.append("output.tool_call_order_mismatch")
    if not {"memory", "reusable_meal", "rescue"}.issubset(
        {str(item) for item in output.get("selected_capabilities") or []}
    ):
        blockers.append("output.selected_capabilities_missing")
    for field in ("action_request", "delivery_request", "mutation_request"):
        if output.get(field) is True:
            blockers.append(f"output.{field}")
    return {"status": "blocked" if blockers else "pass", "blockers": blockers}


def manager_turn_tool_order(runtime_artifact: Mapping[str, Any]) -> list[str]:
    return [
        str(ref).split(":")[-1]
        for ref in runtime_artifact.get("manager_tool_loop_source_refs") or []
    ]


__all__ = [
    "EXPECTED_TOOL_ORDER",
    "manager_turn_output_guard",
    "manager_turn_runtime_blockers",
    "manager_turn_tool_order",
]
