from __future__ import annotations

from types import SimpleNamespace

from app.composition.intake_entry_handoff import entry_handoff_tool_calls
from app.shared.contracts.correction_operation import (
    structured_correction_operation,
    structured_payload_requests_remove_item,
)


def test_structured_correction_operation_accepts_manager_owned_operation_aliases() -> None:
    payload = {
        "target_attachment": {"action_type": "remove_item"},
        "semantic_decision": {"target_attachment": {"correction_type": "remove_item"}},
    }

    assert structured_correction_operation(payload) == "remove_item"
    assert structured_payload_requests_remove_item(payload) is True


def test_structured_correction_operation_does_not_infer_from_raw_text() -> None:
    payload = {"raw_user_input": "remove the soup", "target_attachment": {"canonical_name": "soup"}}

    assert structured_correction_operation(payload) == ""
    assert structured_payload_requests_remove_item(payload) is False


def test_entry_handoff_preserves_manager_owned_action_type_alias() -> None:
    decision = SimpleNamespace(
        workflow_effect="route_to_intake",
        target_attachment={},
        semantic_decision={
            "final_action_candidate": "correction_applied",
            "target_attachment": {
                "meal_thread_id": 1,
                "meal_item_id": 2,
                "canonical_name": "soup",
                "action_type": "remove_item",
            },
        },
    )

    assert entry_handoff_tool_calls(decision) == [
        {
            "name": "resolve_correction_target",
            "arguments": {
                "canonical_name": "soup",
                "meal_thread_id": 1,
                "meal_item_id": 2,
                "operation": "remove_item",
                "target_proposal_source": "entry_manager_handoff",
            },
        }
    ]


def test_entry_handoff_preserves_manager_owned_target_evidence_operation_alias() -> None:
    decision = SimpleNamespace(
        workflow_effect="route_to_intake",
        target_attachment={
            "meal_thread_id": 1,
            "meal_item_id": 2,
            "canonical_name": "soup",
            "target_evidence_operation": "remove_item",
        },
        semantic_decision={
            "final_action_candidate": "correction_applied",
            "target_attachment": {"canonical_name": "soup"},
        },
    )

    assert structured_correction_operation(decision.target_attachment) == "remove_item"
    assert entry_handoff_tool_calls(decision) == [
        {
            "name": "resolve_correction_target",
            "arguments": {
                "canonical_name": "soup",
                "meal_thread_id": 1,
                "meal_item_id": 2,
                "operation": "remove_item",
                "target_proposal_source": "entry_manager_handoff",
            },
        }
    ]


def test_entry_handoff_executes_manager_owned_nutrition_evidence_requirement() -> None:
    decision = SimpleNamespace(
        workflow_effect="route_to_intake",
        target_attachment={"canonical_name": "milk tea"},
        semantic_decision={
            "final_action_candidate": "commit",
            "mutation_intent_candidate": "canonical_write",
            "estimation_posture": "pending_tool_call",
            "base_dish": "milk tea",
            "size_hint": "large",
            "modifier_hints": ["half sugar"],
            "target_attachment": {"mode": "new_meal"},
        },
    )

    assert entry_handoff_tool_calls(decision) == [
        {
            "name": "estimate_nutrition",
            "arguments": {
                "manager_semantic_decision": {
                    "base_dish": "milk tea",
                    "size_hint": "large",
                    "modifier_hints": ["half sugar"],
                    "retrieval_goal": "generic_anchor_lookup",
                    "semantic_authority_source": "live_manager_structured_output",
                },
                "handoff_source": "entry_manager_semantic_decision",
                "deterministic_role": "execute_manager_owned_evidence_requirement_only",
            },
        }
    ]


def test_entry_handoff_executes_correction_target_and_nutrition_requirements() -> None:
    decision = SimpleNamespace(
        workflow_effect="route_to_intake",
        target_attachment={"canonical_name": "chicken rice"},
        semantic_decision={
            "final_action_candidate": "correction_applied",
            "mutation_intent_candidate": "correction_write",
            "estimation_posture": "pending_tool_call",
            "base_dish": "chicken rice",
            "target_attachment": {"mode": "target_committed_thread"},
        },
    )

    assert entry_handoff_tool_calls(decision) == [
        {
            "name": "resolve_correction_target",
            "arguments": {
                "canonical_name": "chicken rice",
                "target_proposal_source": "entry_manager_handoff",
            },
        },
        {
            "name": "estimate_nutrition",
            "arguments": {
                "manager_semantic_decision": {
                    "base_dish": "chicken rice",
                    "retrieval_goal": "generic_anchor_lookup",
                    "semantic_authority_source": "live_manager_structured_output",
                },
                "handoff_source": "entry_manager_semantic_decision",
                "deterministic_role": "execute_manager_owned_evidence_requirement_only",
            },
        },
    ]


def test_entry_handoff_does_not_estimate_composition_unknown_followup() -> None:
    decision = SimpleNamespace(
        workflow_effect="route_to_intake",
        target_attachment={},
        semantic_decision={
            "final_action_candidate": "ask_followup",
            "mutation_intent_candidate": "no_mutation",
            "estimation_posture": "composition_unknown_basket",
            "target_attachment": {},
        },
    )

    assert entry_handoff_tool_calls(decision) == []
