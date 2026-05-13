from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_runtime_bridge_contract import (
    bridge_product_lab_runtime_surface,
)


def build_product_lab_default_manager_script(
    *,
    turn: Mapping[str, Any],
    manager_tool_store_present: bool,
) -> dict[str, Any]:
    bridge_preview = bridge_product_lab_runtime_surface(turn=turn, manager_script=None)
    plan = _mapping(bridge_preview.get("shared_manager_turn_plan_preview"))
    requested_capabilities = [
        str(item.get("capability_id") or "")
        for item in plan.get("requested_capabilities") or []
        if isinstance(item, Mapping)
    ]
    executable_capabilities, omitted_capabilities = _partition_capabilities(
        requested_capabilities=requested_capabilities,
        manager_tool_store_present=manager_tool_store_present,
    )
    manager_script, source_tool_call_ids = _compile_script(executable_capabilities)
    return {
        "artifact_type": "advanced_product_lab_default_manager_script",
        "artifact_schema_version": "1.0",
        "status": "pass" if manager_script else "blocked",
        "planner_bridge_preview": bridge_preview,
        "requested_capabilities": requested_capabilities,
        "executable_capabilities": executable_capabilities,
        "omitted_capabilities": omitted_capabilities,
        "manager_script": manager_script,
        "source_tool_call_ids": source_tool_call_ids,
        "manager_tool_loop_source": "shared_planner_compiled_default",
        "blockers": [] if manager_script else ["compiled_default_manager_script.empty"],
    }


def _partition_capabilities(
    *,
    requested_capabilities: list[str],
    manager_tool_store_present: bool,
) -> tuple[list[str], list[str]]:
    executable: list[str] = []
    omitted: list[str] = []
    for capability_id in requested_capabilities:
        if capability_id == "memory" and not manager_tool_store_present:
            omitted.append("memory.requires_manager_tool_store")
            continue
        if capability_id == "proactive" and not {
            "recommendation",
            "rescue",
        }.issubset(set(requested_capabilities)):
            omitted.append("proactive.requires_recommendation_and_rescue")
            continue
        executable.append(capability_id)
    return executable, omitted


def _compile_script(executable_capabilities: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    source_tool_call_ids: list[str] = []
    script: list[dict[str, Any]] = []
    first_pass_calls: list[dict[str, Any]] = []
    if "memory" in executable_capabilities:
        first_pass_calls.append(
            {
                "call_id": "memory-search-1",
                "tool_name": "memory.search",
                "arguments": {
                    "consumers": [cap for cap in executable_capabilities if cap != "memory"],
                    "token_budget": 200,
                },
            }
        )
        source_tool_call_ids.append("memory-search-1")
    if "query" in executable_capabilities:
        first_pass_calls.append(
            {
                "call_id": "query-1",
                "tool_name": "query.run",
                "arguments": {},
            }
        )
        source_tool_call_ids.append("query-1")
    if first_pass_calls:
        script.append(
            {
                "pass_id": "manager-pass-1",
                "action": "call_tools",
                "tool_calls": first_pass_calls,
            }
        )

    reusable_meal_calls: list[dict[str, Any]] = []
    if "reusable_meal" in executable_capabilities:
        args: dict[str, Any] = {}
        if "memory" in executable_capabilities:
            args["memory_context_call_id"] = "memory-search-1"
        reusable_meal_calls.append(
            {
                "call_id": "reusable-meal-search-1",
                "tool_name": "reusable_meal.search",
                "arguments": args,
            }
        )
        source_tool_call_ids.append("reusable-meal-search-1")
    if reusable_meal_calls:
        script.append(
            {
                "pass_id": f"manager-pass-{len(script) + 1}",
                "action": "call_tools",
                "tool_calls": reusable_meal_calls,
            }
        )

    second_pass_calls: list[dict[str, Any]] = []
    if "recommendation" in executable_capabilities:
        args: dict[str, Any] = {}
        if "memory" in executable_capabilities:
            args["memory_context_call_id"] = "memory-search-1"
        if "query" in executable_capabilities:
            args["query_call_id"] = "query-1"
        second_pass_calls.append(
            {
                "call_id": "recommendation-1",
                "tool_name": "recommendation.run",
                "arguments": args,
            }
        )
        source_tool_call_ids.append("recommendation-1")
    if "rescue" in executable_capabilities:
        second_pass_calls.append(
            {
                "call_id": "rescue-1",
                "tool_name": "rescue.run",
                "arguments": {},
            }
        )
        source_tool_call_ids.append("rescue-1")
    if second_pass_calls:
        script.append(
            {
                "pass_id": f"manager-pass-{len(script) + 1}",
                "action": "call_tools",
                "tool_calls": second_pass_calls,
            }
        )

    if {"recommendation", "rescue", "proactive"}.issubset(set(executable_capabilities)):
        proactive_args: dict[str, Any] = {
            "recommendation_call_id": "recommendation-1",
            "rescue_call_id": "rescue-1",
        }
        if "memory" in executable_capabilities:
            proactive_args["memory_context_call_id"] = "memory-search-1"
        script.append(
            {
                "pass_id": "manager-pass-3",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "call_id": "proactive-1",
                        "tool_name": "proactive.run",
                        "arguments": proactive_args,
                    }
                ],
            }
        )
        source_tool_call_ids.append("proactive-1")

    if source_tool_call_ids:
        script.append(
            {
                "pass_id": f"manager-pass-{len(script) + 1}",
                "action": "final",
                "final_response": {
                    "copy": "Compiled default manager synthesis from shared planner preview.",
                    "source_tool_call_ids": list(source_tool_call_ids),
                },
            }
        )
    return script, source_tool_call_ids


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_product_lab_default_manager_script"]
