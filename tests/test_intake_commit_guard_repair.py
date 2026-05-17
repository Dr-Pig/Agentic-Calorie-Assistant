from __future__ import annotations

from app.composition.intake_commit_guard_repair import commit_boundary_guard_repair_outcome
from app.shared.contracts.intake_results import EstimatePayload


def _blocked_payload() -> EstimatePayload:
    return EstimatePayload(
        request_id="req-repair",
        meal_title="早餐店鐵板麵套餐",
        estimated_kcal=0,
        action_taken="clarify_before_estimate",
        route_target="clarify_user_private",
        trace_contract={
            "canonical_write_decision": {
                "can_write_canonical": False,
                "source": "evidence_unavailable",
                "failure_family": "nutrition_evidence_unavailable",
                "blockers": ["no_approved_runtime_evidence"],
            },
            "blocking_slots": ["nutrition_evidence"],
            "response_mode_hint": "clarify_first",
        },
    )


def test_correction_component_update_guard_repair_requests_manager_owned_listed_item_tool_call() -> None:
    outcome = commit_boundary_guard_repair_outcome(
        payload=_blocked_payload(),
        final_action="correction_applied",
        active_body_plan_present=True,
        correction_target={
            "meal_thread_id": 4,
            "meal_version_id": 4,
            "operation": "update_meal_components",
            "item_candidates": [
                {"canonical_name": "鐵板麵", "estimated_kcal": 420},
                {"canonical_name": "荷包蛋", "estimated_kcal": 90},
                {"canonical_name": "豬肉片", "estimated_kcal": 110},
            ],
        },
        manager_semantic_decision={
            "semantic_authority": "manager_llm",
            "current_turn_intent": "correct_meal",
            "target_attachment": {"operation": "update_meal_components"},
            "final_action_candidate": "correction_applied",
            "mutation_intent_candidate": "correction_write",
        },
    )

    assert outcome is not None
    instruction = outcome["repair_instruction"]
    assert instruction["manager_role"] == "call estimate_nutrition with Manager-owned updated listed_items"
    assert instruction["deterministic_role"] == "reject_evidence_ineligible_commit_only"
    assert instruction["raw_user_input_used"] is False
    assert instruction["deterministic_food_classification_used"] is False
    assert instruction["allowed_repairs"] == [
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
    ]
