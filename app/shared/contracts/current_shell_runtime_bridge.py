from __future__ import annotations

from typing import Any, Mapping

from app.runtime.contracts.manager import IntentType
from app.shared.contracts.manager_turn_plan import (
    CapabilityRequest,
    ManagerTurnPlan,
    ToolCallCandidate,
)


CURRENT_SHELL_INTENT_TO_PRIMARY_WORKFLOW = {
    IntentType.exact_lookup.value: "intake_lookup_or_answer",
    IntentType.estimate.value: "intake_estimate_with_optional_budget_reflection",
    IntentType.ask_followup.value: "clarification_only",
    IntentType.correction.value: "intake_correction_or_removal",
    IntentType.answer_budget.value: "budget_query",
    IntentType.answer_status.value: "status_query",
    IntentType.onboarding.value: "onboarding_bootstrap_required",
}

CURRENT_SHELL_TOOL_TO_SHARED_CANDIDATE = {
    "estimate_nutrition": {"tool_name": "intake.run", "capability_id": "intake"},
    "resolve_correction_target": {"tool_name": "intake.run", "capability_id": "intake"},
    "compare_against_budget": {"tool_name": "query.run", "capability_id": "query"},
    "lookup_generic_food": {"tool_name": "intake.run", "capability_id": "intake"},
    "retrieve_web_food_evidence": {"tool_name": "intake.run", "capability_id": "intake"},
}

FORBIDDEN_MANAGER_TOOLS = {"write_ledger", "persist_meal_log"}


def build_current_shell_runtime_bridge_contract() -> dict[str, Any]:
    return {
        "artifact_type": "current_shell_runtime_bridge_contract",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "upstream_truth_branch": "main",
        "upstream_truth_contract_family": "CurrentShell_ManagerRuntime",
        "current_shell_intent_to_primary_workflow": dict(
            CURRENT_SHELL_INTENT_TO_PRIMARY_WORKFLOW
        ),
        "current_shell_tool_to_shared_candidate": dict(
            CURRENT_SHELL_TOOL_TO_SHARED_CANDIDATE
        ),
        "forbidden_manager_tools": sorted(FORBIDDEN_MANAGER_TOOLS),
        "reparse_raw_user_input_for_semantics": False,
        "llm_output_is_bridge_source_of_semantic_truth": True,
        "deterministic_bridge_role": "map_current_shell_contract_to_shared_planner_vocabulary",
        "blockers": [],
    }


def bridge_current_shell_manager_output(
    manager_output: Mapping[str, Any],
) -> dict[str, Any]:
    source = dict(manager_output)
    source_intent = str(source.get("intent") or "").strip()
    primary_workflow = CURRENT_SHELL_INTENT_TO_PRIMARY_WORKFLOW.get(
        source_intent, "current_shell_bridge_unmapped_intent"
    )
    requested_capabilities = _requested_capabilities_for_intent(source_intent)
    candidate_tool_calls, blockers = _bridge_tool_calls(
        source.get("tool_calls") if isinstance(source.get("tool_calls"), list) else []
    )
    mutation_posture = _mutation_posture(source_intent=source_intent, source=source)
    clarification_posture = (
        "required" if source_intent == IntentType.ask_followup.value else "none"
    )
    response_obligations = ["avoid_hidden_mutation_claims"]
    if source_intent == IntentType.answer_budget.value:
        response_obligations.append("answer_budget_from_runtime_truth_only")
    if source_intent in {
        IntentType.exact_lookup.value,
        IntentType.estimate.value,
        IntentType.correction.value,
    }:
        response_obligations.append("show_budget_impact_only_if_tool_backed")
    if primary_workflow == "current_shell_bridge_unmapped_intent":
        blockers.append(f"current_shell_intent_unmapped:{source_intent or 'missing'}")
    plan = ManagerTurnPlan(
        primary_workflow=primary_workflow,
        secondary_intents=[],
        requested_capabilities=requested_capabilities,
        candidate_tool_calls=candidate_tool_calls,
        ordering_constraints=_ordering_constraints(requested_capabilities),
        mutation_posture=mutation_posture,
        clarification_posture=clarification_posture,
        response_obligations=response_obligations,
        omission_candidates=[],
        scope_keys={},
    )
    return {
        "artifact_type": "current_shell_runtime_bridge_preview",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "source_manager_action": str(source.get("manager_action") or ""),
        "source_intent": source_intent,
        "source_workflow_effect": str(source.get("workflow_effect") or ""),
        "shared_manager_turn_plan_preview": plan.model_dump(mode="json"),
        "bridge_uses_current_shell_llm_output_only": True,
        "raw_user_input_semantic_reparse_used": False,
        "blockers": blockers,
    }


def _requested_capabilities_for_intent(source_intent: str) -> list[CapabilityRequest]:
    if source_intent in {
        IntentType.exact_lookup.value,
        IntentType.estimate.value,
        IntentType.correction.value,
    }:
        return [
            CapabilityRequest(capability_id="intake", request_mode="required", priority=1),
            CapabilityRequest(capability_id="query", request_mode="optional", priority=2),
        ]
    if source_intent in {IntentType.answer_budget.value, IntentType.answer_status.value}:
        return [CapabilityRequest(capability_id="query", request_mode="required", priority=1)]
    if source_intent == IntentType.ask_followup.value:
        return [CapabilityRequest(capability_id="intake", request_mode="required", priority=1)]
    return []


def _bridge_tool_calls(
    raw_tool_calls: list[Any],
) -> tuple[list[ToolCallCandidate], list[str]]:
    candidates: list[ToolCallCandidate] = []
    blockers: list[str] = []
    for raw_call in raw_tool_calls:
        if not isinstance(raw_call, Mapping):
            blockers.append("current_shell_tool_call_not_mapping")
            continue
        raw_name = str(raw_call.get("name") or raw_call.get("tool_name") or "").strip()
        if raw_name in FORBIDDEN_MANAGER_TOOLS:
            blockers.append(f"current_shell_forbidden_manager_tool:{raw_name}")
            continue
        mapped = CURRENT_SHELL_TOOL_TO_SHARED_CANDIDATE.get(raw_name)
        if mapped is None:
            blockers.append(f"current_shell_tool_unmapped:{raw_name or 'missing'}")
            continue
        candidates.append(
            ToolCallCandidate(
                tool_name=str(mapped["tool_name"]),
                capability_id=str(mapped["capability_id"]),
            )
        )
    return candidates, blockers


def _mutation_posture(*, source_intent: str, source: Mapping[str, Any]) -> str:
    if source_intent in {IntentType.answer_budget.value, IntentType.answer_status.value}:
        return "read_only"
    if source_intent == IntentType.onboarding.value:
        return "read_only"
    final_action = str(source.get("final_action") or "").strip()
    workflow_effect = str(source.get("workflow_effect") or "").strip()
    if final_action in {"commit", "correction_applied"}:
        return "mutation_guarded"
    if workflow_effect in {"no_mutation", "query_only", "draft_clarify_no_mutation"}:
        return "read_only"
    return "mutation_guarded"


def _ordering_constraints(
    requested_capabilities: list[CapabilityRequest],
) -> list[str]:
    return []


__all__ = [
    "CURRENT_SHELL_INTENT_TO_PRIMARY_WORKFLOW",
    "CURRENT_SHELL_TOOL_TO_SHARED_CANDIDATE",
    "FORBIDDEN_MANAGER_TOOLS",
    "bridge_current_shell_manager_output",
    "build_current_shell_runtime_bridge_contract",
]
