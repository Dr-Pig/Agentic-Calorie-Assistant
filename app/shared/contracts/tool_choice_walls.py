from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.capability_registry import build_shared_capability_registry


FORBIDDEN_MUTATION_FLAGS = {
    "canonical_mutation",
    "canonical_mutation_allowed",
    "canonical_product_mutation_allowed",
    "canonical_product_mutation_allowed_on_main",
    "direct_ledger_commit",
    "durable_product_memory_activation_allowed",
    "durable_product_memory_written",
    "ledger_entry_created",
    "mainline_activation_enabled",
    "meal_thread_mutated",
    "production_db_migration_allowed",
    "production_route_or_api_mount_allowed",
    "production_scheduler_delivery_allowed",
    "scheduler_delivery_allowed",
}


def validate_tool_choice_walls(
    *,
    requested_capability_ids: list[str],
    tool_calls: list[Mapping[str, Any]],
    ordering_constraints: list[str],
) -> dict[str, Any]:
    shared_registry = build_shared_capability_registry()
    known_tools = set(shared_registry["shared_tool_vocabulary"])
    tool_by_capability = {
        str(item["capability_id"]): str(item["shared_tool_name"])
        for item in shared_registry["capabilities"]
    }
    blockers: list[str] = []
    seen_by_tool: dict[str, int] = {}

    for index, call in enumerate(tool_calls):
        tool_name = str(call.get("tool_name") or "")
        capability_id = str(call.get("capability_id") or "")
        arguments = call.get("arguments")
        if tool_name not in known_tools:
            blockers.append(f"tool.unsupported:{tool_name or 'missing'}")
        if capability_id and capability_id not in requested_capability_ids:
            blockers.append(f"tool.capability_not_requested:{capability_id}")
        if not isinstance(arguments, Mapping):
            blockers.append(f"tool.arguments_not_mapping:{tool_name or 'missing'}")
        else:
            blockers.extend(_mutation_flag_blockers(tool_name=tool_name, payload=arguments))
        blockers.extend(_mutation_flag_blockers(tool_name=tool_name, payload=call))
        seen_by_tool.setdefault(tool_name, index)

    blockers.extend(
        _ordering_blockers(
            seen_by_tool=seen_by_tool,
            ordering_constraints=ordering_constraints,
            tool_by_capability=tool_by_capability,
        )
    )
    return {
        "artifact_type": "shared_tool_choice_walls_validation",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "requested_capability_ids": requested_capability_ids,
        "tool_order": [str(call.get("tool_name") or "") for call in tool_calls],
        "ordering_constraints_checked": ordering_constraints,
        "mutation_guard_checked": True,
        "blockers": blockers,
    }


def _ordering_blockers(
    *,
    seen_by_tool: Mapping[str, int],
    ordering_constraints: list[str],
    tool_by_capability: Mapping[str, str],
) -> list[str]:
    blockers: list[str] = []
    for constraint in ordering_constraints:
        if "_before_" not in constraint:
            blockers.append(f"ordering_constraint_unknown:{constraint}")
            continue
        first_capability, second_capability = constraint.split("_before_", 1)
        first_tool = tool_by_capability.get(first_capability)
        second_tool = tool_by_capability.get(second_capability)
        if not first_tool or not second_tool:
            blockers.append(f"ordering_constraint_unknown:{constraint}")
            continue
        blockers.extend(_must_precede(seen_by_tool, first_tool, second_tool, constraint))
    return blockers


def _mutation_flag_blockers(*, tool_name: str, payload: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    for field in sorted(FORBIDDEN_MUTATION_FLAGS):
        if payload.get(field) is True:
            blockers.append(f"tool.mutation_flag_forbidden:{tool_name or 'missing'}.{field}")
    return blockers


def _must_precede(
    seen_by_tool: Mapping[str, int],
    first_tool: str,
    second_tool: str,
    constraint: str,
) -> list[str]:
    if first_tool not in seen_by_tool or second_tool not in seen_by_tool:
        return []
    return (
        []
        if seen_by_tool[first_tool] < seen_by_tool[second_tool]
        else [f"ordering_constraint_failed:{constraint}"]
    )


__all__ = ["validate_tool_choice_walls"]
