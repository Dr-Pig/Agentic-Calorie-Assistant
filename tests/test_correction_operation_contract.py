from __future__ import annotations

from types import SimpleNamespace

from app.composition.intake_entry_handoff import entry_handoff_tool_calls
from app.shared.contracts.correction_operation import (
    structured_correction_operation,
    structured_payload_requests_remove_item,
    structured_payload_requests_thread_level_correction,
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
    assert structured_payload_requests_thread_level_correction(payload) is False


def test_structured_correction_operation_identifies_thread_level_correction() -> None:
    payload = {"semantic_decision": {"target_attachment": {"operation": "correct_active_meal"}}}

    assert structured_correction_operation(payload) == "correct_active_meal"
    assert structured_payload_requests_thread_level_correction(payload) is True
    assert structured_payload_requests_remove_item(payload) is False


def test_structured_correction_operation_accepts_manager_correct_meal_alias() -> None:
    payload = {"target_attachment": {"operation": "correct_meal"}}

    assert structured_correction_operation(payload) == "correct_meal"
    assert structured_payload_requests_thread_level_correction(payload) is True


def test_structured_correction_operation_accepts_manager_owned_whole_meal_removal() -> None:
    payload = {"semantic_decision": {"target_attachment": {"operation": "remove_meal"}}}

    assert structured_correction_operation(payload) == "remove_meal"
    assert structured_payload_requests_thread_level_correction(payload) is True
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


def test_entry_handoff_hydrates_manager_selected_target_name_from_state() -> None:
    decision = SimpleNamespace(
        workflow_effect="route_to_intake",
        target_attachment={},
        semantic_decision={
            "final_action_candidate": "commit",
            "mutation_intent_candidate": "canonical_write",
            "estimation_posture": "pending_tool_call",
            "target_attachment": {
                "operation": "attach_to_pending_followup",
                "target_meal_id": 1,
                "source_meal_id": 1,
            },
        },
    )
    resolved_state = SimpleNamespace(
        active_meal={
            "meal_thread_id": 1,
            "meal_item_id": 1,
            "canonical_name": "\u73cd\u73e0\u5976\u8336",
        },
    )

    calls = entry_handoff_tool_calls(decision, resolved_state=resolved_state)

    assert calls[0]["arguments"]["manager_semantic_decision"]["base_dish"] == "\u73cd\u73e0\u5976\u8336"


def test_entry_handoff_hydrates_pending_followup_legacy_target_to_active_thread() -> None:
    decision = SimpleNamespace(
        workflow_effect="route_to_intake",
        target_attachment={},
        semantic_decision={
            "final_action_candidate": "correction_applied",
            "mutation_intent_candidate": "correction_write",
            "estimation_posture": "pending_tool_call",
            "target_attachment": {
                "operation": "attach_to_pending_followup",
                "target_resolution_source": "pending_followup_state",
                "meal_id": 7,
                "source_meal_id": 7,
            },
            "base_dish": "\u73cd\u5976",
            "size_hint": "\u4e2d\u676f",
            "modifier_hints": ["\u534a\u7cd6"],
            "retrieval_goal": "generic_anchor_lookup",
        },
    )
    resolved_state = SimpleNamespace(
        active_meal={
            "meal_thread_id": 3,
            "meal_item_id": 4,
            "meal_title": "\u73cd\u73e0\u5976\u8336",
            "canonical_name": "\u73cd\u73e0\u5976\u8336",
        },
    )

    calls = entry_handoff_tool_calls(decision, resolved_state=resolved_state)

    assert calls[0]["name"] == "resolve_correction_target"
    assert calls[0]["arguments"]["meal_thread_id"] == 3
    assert calls[0]["arguments"]["meal_item_id"] == 4
    assert calls[1]["name"] == "estimate_nutrition"
    assert calls[1]["arguments"]["manager_semantic_decision"]["base_dish"] == "\u73cd\u5976"


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


def test_entry_handoff_preserves_manager_owned_thread_level_correction_operation() -> None:
    decision = SimpleNamespace(
        workflow_effect="route_to_intake",
        target_attachment={},
        semantic_decision={
            "final_action_candidate": "correction_applied",
            "mutation_intent_candidate": "correction_write",
            "estimation_posture": "pending_tool_call",
            "target_attachment": {
                "meal_thread_id": 3,
                "meal_version_id": 4,
                "operation": "correct_active_meal",
            },
            "listed_items": ["teppan noodles half", "egg"],
            "retrieval_goal": "listed_item_lookup",
        },
    )

    assert entry_handoff_tool_calls(decision) == [
        {
            "name": "resolve_correction_target",
            "arguments": {
                "meal_thread_id": 3,
                "operation": "correct_active_meal",
                "target_proposal_source": "entry_manager_handoff",
            },
        },
        {
            "name": "estimate_nutrition",
            "arguments": {
                "manager_semantic_decision": {
                    "listed_items": ["teppan noodles half", "egg"],
                    "retrieval_goal": "listed_item_lookup",
                    "semantic_authority_source": "live_manager_structured_output",
                },
                "handoff_source": "entry_manager_semantic_decision",
                "deterministic_role": "execute_manager_owned_evidence_requirement_only",
            },
        },
    ]


def test_entry_handoff_preserves_manager_owned_whole_meal_removal_without_nutrition_tool() -> None:
    decision = SimpleNamespace(
        workflow_effect="route_to_intake",
        target_attachment={},
        semantic_decision={
            "final_action_candidate": "correction_applied",
            "mutation_intent_candidate": "correction_write",
            "estimation_posture": "target_evidence_needed",
            "target_attachment": {
                "meal_thread_id": 3,
                "meal_version_id": 4,
                "operation": "remove_meal",
                "target_resolution_source": "named_slot_match",
            },
        },
    )

    assert entry_handoff_tool_calls(decision) == [
        {
            "name": "resolve_correction_target",
            "arguments": {
                "meal_thread_id": 3,
                "operation": "remove_meal",
                "target_resolution_source": "named_slot_match",
                "target_proposal_source": "entry_manager_handoff",
            },
        }
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
