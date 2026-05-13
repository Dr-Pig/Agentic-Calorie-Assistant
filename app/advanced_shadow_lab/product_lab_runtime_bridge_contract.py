from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.manager_turn_plan import (
    CapabilityRequest,
    ManagerTurnPlan,
    ToolCallCandidate,
)


FIXTURE_INTENT_TO_PLAN = {
    "advanced_recommendation_rescue_proactive_loop": {
        "primary_workflow": "advanced_recommendation_rescue_proactive_loop",
        "requested_capabilities": ["memory", "recommendation", "rescue", "proactive"],
    },
    "calibration_proposal_from_body_trend": {
        "primary_workflow": "calibration_from_body_trend",
        "requested_capabilities": ["proactive"],
    },
    "no_plan_degraded_journey": {
        "primary_workflow": "no_plan_degraded_guidance",
        "requested_capabilities": ["recommendation", "rescue"],
    },
    "pre_meal_planning": {
        "primary_workflow": "pre_meal_planning_guidance",
        "requested_capabilities": ["recommendation", "rescue"],
    },
    "planned_event_all_day_allocation": {
        "primary_workflow": "planned_event_all_day_allocation",
        "requested_capabilities": ["recommendation", "rescue", "proactive"],
    },
    "swap_suggestion": {
        "primary_workflow": "swap_suggestion",
        "requested_capabilities": ["recommendation"],
    },
    "exercise_budget_bonus": {
        "primary_workflow": "exercise_budget_bonus",
        "requested_capabilities": ["query", "recommendation"],
    },
    "weekly_insight_proactive_lab": {
        "primary_workflow": "weekly_insight_proactive",
        "requested_capabilities": ["memory", "proactive"],
    },
    "repeat_meal_intake_shadow": {
        "primary_workflow": "repeat_meal_intake_shadow",
        "requested_capabilities": ["memory", "reusable_meal"],
    },
    "repeat_meal_rescue_shadow": {
        "primary_workflow": "repeat_meal_rescue_shadow",
        "requested_capabilities": ["memory", "reusable_meal", "rescue"],
    },
    "multi_intent_recommendation_e2e": {
        "primary_workflow": "multi_intent_recommendation_e2e",
        "requested_capabilities": [
            "query",
            "memory",
            "reusable_meal",
            "recommendation",
            "rescue",
            "proactive",
        ],
    },
}


def build_product_lab_runtime_bridge_contract() -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_runtime_bridge_contract",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "upstream_truth_branch": "main",
        "upstream_truth_contract_family": "CurrentShell_ManagerRuntime",
        "bridge_scope": "advanced_lab_runtime_surfaces_to_shared_planner_vocabulary",
        "supported_fixture_intents": sorted(FIXTURE_INTENT_TO_PLAN),
        "manager_script_tool_names_already_use_shared_vocabulary": True,
        "direct_runtime_bypass_is_transitional_not_upstream_truth": True,
        "raw_user_input_semantic_reparse_used": False,
        "blockers": [],
    }


def bridge_product_lab_runtime_surface(
    *,
    turn: Mapping[str, Any],
    manager_script: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    fixture_intent = str(turn.get("semantic_intent_fixture") or "").strip()
    source = FIXTURE_INTENT_TO_PLAN.get(fixture_intent)
    blockers: list[str] = []
    if source is None:
        blockers.append(f"product_lab_fixture_intent_unmapped:{fixture_intent or 'missing'}")
        requested_capabilities: list[CapabilityRequest] = []
        primary_workflow = "product_lab_runtime_bridge_unmapped_fixture_intent"
    else:
        requested_capabilities = [
            CapabilityRequest(capability_id=capability_id, request_mode="required", priority=index + 1)
            for index, capability_id in enumerate(source["requested_capabilities"])
        ]
        primary_workflow = str(source["primary_workflow"])
    candidate_tool_calls, tool_blockers = _tool_candidates_from_manager_script(manager_script or [])
    blockers.extend(tool_blockers)
    plan = ManagerTurnPlan(
        primary_workflow=primary_workflow,
        secondary_intents=[],
        requested_capabilities=requested_capabilities,
        candidate_tool_calls=candidate_tool_calls,
        ordering_constraints=[],
        mutation_posture="proposal_only",
        clarification_posture="none",
        response_obligations=["avoid_hidden_mutation_claims", "chat_first_surface_only"],
        omission_candidates=[],
        scope_keys={"surface": str(turn.get("surface") or "")},
    )
    return {
        "artifact_type": "advanced_product_lab_runtime_bridge_preview",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "source_fixture_intent": fixture_intent,
        "manager_script_present": manager_script is not None,
        "direct_runtime_bypass_present": manager_script is None,
        "shared_manager_turn_plan_preview": plan.model_dump(mode="json"),
        "shared_tool_vocabulary_used": True,
        "raw_user_input_semantic_reparse_used": False,
        "blockers": blockers,
    }


def _tool_candidates_from_manager_script(
    manager_script: list[Mapping[str, Any]],
) -> tuple[list[ToolCallCandidate], list[str]]:
    candidates: list[ToolCallCandidate] = []
    blockers: list[str] = []
    for step in manager_script:
        if str(step.get("action") or "") != "call_tools":
            continue
        for raw_call in step.get("tool_calls") or []:
            if not isinstance(raw_call, Mapping):
                blockers.append("product_lab_manager_script_tool_call_not_mapping")
                continue
            tool_name = str(raw_call.get("tool_name") or raw_call.get("name") or "").strip()
            capability_id = _capability_id_for_tool_name(tool_name)
            if capability_id is None:
                blockers.append(f"product_lab_manager_script_tool_unmapped:{tool_name or 'missing'}")
                continue
            candidates.append(
                ToolCallCandidate(tool_name=tool_name, capability_id=capability_id)
            )
    return candidates, blockers


def _capability_id_for_tool_name(tool_name: str) -> str | None:
    if tool_name.startswith("memory.") or tool_name == "conversation_recall.search":
        return "memory"
    if tool_name == "query.run":
        return "query"
    if tool_name == "recommendation.run":
        return "recommendation"
    if tool_name == "rescue.run":
        return "rescue"
    if tool_name == "proactive.run":
        return "proactive"
    if tool_name == "reusable_meal.search":
        return "reusable_meal"
    return None


__all__ = [
    "FIXTURE_INTENT_TO_PLAN",
    "bridge_product_lab_runtime_surface",
    "build_product_lab_runtime_bridge_contract",
]
