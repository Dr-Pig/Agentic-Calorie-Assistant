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
