from __future__ import annotations

from typing import Any

from app.composition.commit_boundary_preflight import run_commit_boundary_preflight
from app.composition.commit_boundary_preflight import NAMED_FOOD_KCAL_CONFLICT_REQUIRES_CONFIRMATION
from app.shared.contracts.correction_operation import structured_correction_operation
from app.shared.contracts.intake_results import EstimatePayload


def _repair_instruction_for_failure(
    failure_family: str | None,
    *,
    manager_semantic_decision: dict[str, Any],
    correction_target: Any,
) -> dict[str, Any]:
    if failure_family == NAMED_FOOD_KCAL_CONFLICT_REQUIRES_CONFIRMATION:
        return {
            "role": "bounded_manager_repair",
            "deterministic_role": "reject_conflicting_user_kcal_commit_only",
            "manager_role": "ask user to confirm the provided kcal or portion before committing",
            "allowed_repairs": [
                {
                    "manager_action": "final",
                    "final_action": "ask_followup",
                    "workflow_effect": "ask_followup",
                    "tool_calls": [],
                    "semantic_decision": {
                        "source": "named_food_user_kcal_conflict",
                        "final_action_candidate": "ask_followup",
                        "mutation_intent_candidate": "no_mutation",
                        "estimation_posture": "user_kcal_plausibility_check",
                    },
                }
            ],
        }
    if _manager_can_repair_component_update_with_listed_item_tool(
        manager_semantic_decision=manager_semantic_decision,
        correction_target=correction_target,
    ):
        return {
            "role": "bounded_manager_repair",
            "deterministic_role": "reject_evidence_ineligible_commit_only",
            "manager_role": "call estimate_nutrition with Manager-owned updated listed_items",
            "raw_user_input_used": False,
            "deterministic_food_classification_used": False,
            "allowed_repairs": [
                {
                    "manager_action": "call_tools",
                    "final_action": "correction_applied",
                    "workflow_effect": "correction",
                    "required_tool": "estimate_nutrition",
                    "semantic_decision": {
                        "current_turn_intent": "correct_meal",
                        "final_action_candidate": "correction_applied",
                        "mutation_intent_candidate": "correction_write",
                        "target_attachment": {"operation": "update_meal_components"},
                        "retrieval_goal": "listed_item_lookup",
                        "listed_items": "manager_owned_updated_component_list_required",
                    },
                },
                {
                    "manager_action": "final",
                    "final_action": "ask_followup",
                    "workflow_effect": "ask_followup",
                    "tool_calls": [],
                    "semantic_decision": {
                        "final_action_candidate": "ask_followup",
                        "mutation_intent_candidate": "no_mutation",
                        "estimation_posture": "composition_unknown_basket",
                    },
                },
            ],
        }
    return {
        "role": "bounded_manager_repair",
        "deterministic_role": "reject_evidence_ineligible_commit_only",
        "manager_role": "choose legal final action",
        "allowed_repairs": [
            {
                "manager_action": "final",
                "final_action": "ask_followup",
                "workflow_effect": "ask_followup",
                "tool_calls": [],
                "semantic_decision": {
                    "final_action_candidate": "ask_followup",
                    "mutation_intent_candidate": "no_mutation",
                    "estimation_posture": "composition_unknown_basket",
                },
            }
        ],
    }


def _manager_can_repair_component_update_with_listed_item_tool(
    *,
    manager_semantic_decision: dict[str, Any],
    correction_target: Any,
) -> bool:
    decision = dict(manager_semantic_decision or {})
    target = dict(correction_target or {}) if isinstance(correction_target, dict) else {}
    if str(decision.get("current_turn_intent") or "") != "correct_meal":
        return False
    if str(decision.get("final_action_candidate") or "") != "correction_applied":
        return False
    if str(decision.get("mutation_intent_candidate") or "") != "correction_write":
        return False
    semantic_target = decision.get("target_attachment")
    merged_target = {
        **target,
        **(semantic_target if isinstance(semantic_target, dict) else {}),
    }
    if structured_correction_operation(merged_target) != "update_meal_components":
        return False
    item_candidates = target.get("item_candidates")
    return isinstance(item_candidates, list) and any(isinstance(item, dict) for item in item_candidates)


def commit_boundary_guard_repair_outcome(
    *,
    payload: EstimatePayload | None,
    final_action: str,
    active_body_plan_present: bool,
    correction_target: Any,
    manager_semantic_decision: dict[str, Any],
    transition_preflight_trace: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if final_action not in {"commit", "correction_applied", "overshoot_note"} or payload is None:
        return None
    commit_preflight = run_commit_boundary_preflight(
        payload=payload,
        manager_final_action=final_action,
        active_body_plan_present=active_body_plan_present,
        correction_target=correction_target,
        manager_semantic_decision=manager_semantic_decision,
    )
    if not commit_preflight.blocked:
        return None
    failure_family = commit_preflight.failure_family or "phase_a_commit_boundary_blocked"
    return {
        "ok": False,
        "repair_request": True,
        "failure_family": failure_family,
        "guard_feedback_source": {
            "source": "commit_evidence_policy",
            "input_authority": "manager_owned_candidate_evidence",
            "input_kind": "nutrition_evidence_packet",
            "manager_semantic_authority": str(manager_semantic_decision.get("semantic_authority") or ""),
            "raw_user_input_used": False,
            "deterministic_food_classification_used": False,
        },
        "deterministic_final_action": False,
        "deterministic_followup_text": False,
        "phase_a_transition_guard_preflight": dict(transition_preflight_trace or {}),
        "phase_a_commit_boundary_preflight": commit_preflight.trace_payload(),
        "repair_instruction": _repair_instruction_for_failure(
            failure_family,
            manager_semantic_decision=dict(manager_semantic_decision or {}),
            correction_target=correction_target,
        ),
    }
