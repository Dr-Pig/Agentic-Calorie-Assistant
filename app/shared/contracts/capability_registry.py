from __future__ import annotations

from typing import Any


def build_shared_capability_registry() -> dict[str, Any]:
    capabilities = [
        _capability(
            capability_id="intake",
            capability_family="intake",
            shared_tool_name="intake.run",
            truth_owner="meal_thread",
            tool_binding_status="bridge_required",
            primary_surface="chat",
        ),
        _capability(
            capability_id="query",
            capability_family="query",
            shared_tool_name="query.run",
            truth_owner="day_budget_ledger",
            tool_binding_status="implemented_in_lab",
            primary_surface="chat",
        ),
        _capability(
            capability_id="memory",
            capability_family="long_term_memory",
            shared_tool_name="memory.search",
            truth_owner="memory_record",
            tool_binding_status="implemented_in_lab",
            primary_surface="chat",
        ),
        _capability(
            capability_id="recommendation",
            capability_family="recommendation",
            shared_tool_name="recommendation.run",
            truth_owner="proposal",
            tool_binding_status="implemented_in_lab",
            primary_surface="chat",
        ),
        _capability(
            capability_id="rescue",
            capability_family="rescue",
            shared_tool_name="rescue.run",
            truth_owner="proposal",
            tool_binding_status="implemented_in_lab",
            primary_surface="chat",
        ),
        _capability(
            capability_id="proactive",
            capability_family="proactive",
            shared_tool_name="proactive.run",
            truth_owner="proposal",
            tool_binding_status="implemented_in_lab",
            primary_surface="chat",
        ),
        _capability(
            capability_id="reusable_meal",
            capability_family="reusable_meal",
            shared_tool_name="reusable_meal.search",
            truth_owner="reusable_meal_entity",
            tool_binding_status="implemented_in_lab",
            primary_surface="chat",
        ),
        _capability(
            capability_id="pending_meal_intent",
            capability_family="short_term_context",
            shared_tool_name="pending_meal_intent.update",
            truth_owner="pending_meal_intent",
            tool_binding_status="implemented_in_lab",
            primary_surface="chat",
        ),
    ]
    return {
        "artifact_type": "shared_capability_registry",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "capabilities": capabilities,
        "shared_tool_vocabulary": [item["shared_tool_name"] for item in capabilities],
        "planner_reads_capability_ids_not_raw_branch_paths": True,
        "branch_specific_activation_is_separate_from_registry": True,
        "blockers": [],
    }


def _capability(
    *,
    capability_id: str,
    capability_family: str,
    shared_tool_name: str,
    truth_owner: str,
    tool_binding_status: str,
    primary_surface: str,
) -> dict[str, Any]:
    return {
        "capability_id": capability_id,
        "capability_family": capability_family,
        "shared_tool_name": shared_tool_name,
        "truth_owner": truth_owner,
        "tool_binding_status": tool_binding_status,
        "primary_surface": primary_surface,
        "manager_style_runtime_required": True,
    }


__all__ = ["build_shared_capability_registry"]
