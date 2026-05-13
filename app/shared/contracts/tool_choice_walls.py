from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.capability_registry import build_shared_capability_registry


def validate_tool_choice_walls(
    *,
    requested_capability_ids: list[str],
    tool_calls: list[Mapping[str, Any]],
    ordering_constraints: list[str],
) -> dict[str, Any]:
    shared_registry = build_shared_capability_registry()
    known_tools = set(shared_registry["shared_tool_vocabulary"])
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
        seen_by_tool.setdefault(tool_name, index)

    blockers.extend(
        _ordering_blockers(seen_by_tool=seen_by_tool, ordering_constraints=ordering_constraints)
    )
    return {
        "artifact_type": "shared_tool_choice_walls_validation",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
    }


def _ordering_blockers(
    *, seen_by_tool: Mapping[str, int], ordering_constraints: list[str]
) -> list[str]:
    blockers: list[str] = []
    for constraint in ordering_constraints:
        if constraint == "intake_before_rescue":
            blockers.extend(_must_precede(seen_by_tool, "intake.run", "rescue.run", constraint))
        elif constraint == "rescue_before_recommendation":
            blockers.extend(
                _must_precede(seen_by_tool, "rescue.run", "recommendation.run", constraint)
            )
        elif constraint == "proactive_before_recommendation":
            blockers.extend(
                _must_precede(seen_by_tool, "proactive.run", "recommendation.run", constraint)
            )
        elif constraint == "query_before_memory":
            blockers.extend(
                _must_precede(seen_by_tool, "query.run", "memory.search", constraint)
            )
        elif constraint == "reusable_meal_before_intake":
            blockers.extend(
                _must_precede(seen_by_tool, "reusable_meal.search", "intake.run", constraint)
            )
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
