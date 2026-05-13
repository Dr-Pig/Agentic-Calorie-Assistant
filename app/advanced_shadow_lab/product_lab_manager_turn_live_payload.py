from __future__ import annotations

from typing import Any, Mapping


def manager_turn_live_provider_payload(
    runtime_artifact: Mapping[str, Any],
    *,
    constraints: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "diagnostic_task": "Assess one advanced product-lab Manager turn.",
        "runtime_summary": _runtime_summary(runtime_artifact),
        "output_contract": {
            "required_fields": [
                "claim_scope",
                "selected_capabilities",
                "tool_call_order",
                "manager_turn_summary",
                "action_request",
                "delivery_request",
                "mutation_request",
                "risk_notes",
            ],
            "claim_scope": "diagnostic_only",
            "expected_tool_call_order": ["memory.search", "reusable_meal.search", "rescue.run"],
            "must_not_request": ["outside_lab_delivery", "canonical_mutation", "scheduler_delivery"],
        },
        "constraints": dict(constraints),
    }


def _runtime_summary(runtime_artifact: Mapping[str, Any]) -> dict[str, Any]:
    compiled = _mapping(runtime_artifact.get("compiled_default_manager_script"))
    memory = _mapping(runtime_artifact.get("manager_selected_memory_context_adapter"))
    reusable = _mapping(runtime_artifact.get("manager_selected_reusable_meal_artifact"))
    rescue = _mapping(runtime_artifact.get("manager_selected_rescue_artifact"))
    return {
        "source_artifact_type": str(runtime_artifact.get("artifact_type") or ""),
        "source_status": str(runtime_artifact.get("status") or ""),
        "semantic_intent_fixture": str(runtime_artifact.get("semantic_intent_fixture") or ""),
        "requested_capabilities": [
            str(item) for item in compiled.get("requested_capabilities") or []
        ],
        "manager_tool_order": _tool_order(runtime_artifact),
        "selected_memory_record_ids": [
            str(item)
            for item in _mapping(memory.get("memory_record_summary")).get("selected_record_ids") or []
        ],
        "reusable_meal_candidates": [
            {
                "entity_id": str(item.get("entity_id") or ""),
                "estimate_posture_decision": str(item.get("estimate_posture_decision") or ""),
            }
            for item in reusable.get("reusable_meal_candidates") or []
            if isinstance(item, Mapping)
        ],
        "rescue_presented_to_lab": rescue.get("proposal_presented_to_lab") is True,
        "rescue_primary_actions": [str(item) for item in rescue.get("primary_actions") or []],
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
    }


def _tool_order(runtime_artifact: Mapping[str, Any]) -> list[str]:
    order: list[str] = []
    for ref in runtime_artifact.get("manager_tool_loop_source_refs") or []:
        parts = str(ref).split(":")
        if len(parts) >= 3:
            order.append(parts[-1])
    return order


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["manager_turn_live_provider_payload"]
