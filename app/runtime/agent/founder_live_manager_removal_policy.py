from __future__ import annotations

from typing import Any

from app.shared.contracts.correction_operation import (
    structured_payload_requests_remove_item,
    structured_payload_requests_remove_meal,
)

EXPLICIT_WHOLE_MEAL_REMOVAL_RULE = {
    "semantic_intent": "correct_meal",
    "workflow_family": "correction",
    "operation": "remove_meal",
    "evidence_type": "target_evidence",
    "nutrition_evidence_required": False,
    "manager_role": "select_meal_thread_or_ask_target_clarification",
    "runtime_role": "validate_manager_selected_thread_id_and_version_removal",
    "forbidden": ["hard_delete", "raw_text_deterministic_routing", "slot_keyword_target_selection"],
}

REMOVAL_CONTRACT_EXAMPLE = {
    "name": "explicit_item_or_whole_meal_removal_as_correction",
    "valid": {
        "manager_action": "call_tools",
        "tool_calls": [
            {
                "name": "resolve_correction_target",
                "arguments": {"canonical_name": "soup", "operation": "remove_item"},
            }
        ],
        "final_action": "correction_applied",
        "semantic_decision": {
            "current_turn_intent": "correct_meal",
            "final_action_candidate": "correction_applied",
            "mutation_intent_candidate": "correction_write",
            "target_attachment": {"operation": "remove_item"},
        },
    },
    "valid_whole_meal_after_target_evidence": {
        "manager_action": "final",
        "final_action": "correction_applied",
        "target_attachment": {"operation": "remove_meal", "meal_thread_id": "validated_thread"},
        "semantic_decision": {
            "current_turn_intent": "correct_meal",
            "final_action_candidate": "correction_applied",
            "mutation_intent_candidate": "correction_write",
            "target_attachment": {"operation": "remove_meal"},
        },
    },
    "invalid": {
        "manager_action": "final",
        "final_action": "commit",
        "semantic_decision": {
            "current_turn_intent": "log_meal",
            "mutation_intent_candidate": "meal_log_write",
        },
    },
}


def target_evidence_requests_remove_item(evidence_state: Any) -> bool:
    return _target_evidence_present(evidence_state) and isinstance(evidence_state, dict) and str(evidence_state.get("target_evidence_operation") or "") == "remove_item"


def target_evidence_requests_remove_meal(evidence_state: Any) -> bool:
    return _target_evidence_present(evidence_state) and isinstance(evidence_state, dict) and str(evidence_state.get("target_evidence_operation") or "") == "remove_meal"


def target_evidence_requests_removal(evidence_state: Any) -> bool:
    return target_evidence_requests_remove_item(evidence_state) or target_evidence_requests_remove_meal(evidence_state)


def payload_requests_removal(payload: dict[str, Any] | None) -> bool:
    return structured_payload_requests_remove_item(payload) or structured_payload_requests_remove_meal(payload)


def _target_evidence_present(evidence_state: Any) -> bool:
    return isinstance(evidence_state, dict) and evidence_state.get("target_evidence_present") is True
