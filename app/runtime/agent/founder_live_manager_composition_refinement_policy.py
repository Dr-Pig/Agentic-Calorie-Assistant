from __future__ import annotations

from typing import Any


COMPOSITION_REFINEMENT_AFTER_BASIS_QUERY_RULE: dict[str, Any] = {
    "semantic_intent": "correct_meal",
    "intent_type": "correct_meal",
    "workflow_family": "composition_refinement_after_estimate_basis_query",
    "required_tool_when_evidence_missing": "estimate_nutrition",
    "mutation_intent_candidate": "correction_write",
    "forbidden_substitute_final_actions": ["answer_only", "ask_followup_for_replacement_confirmation"],
    "runtime_role": "validate_evidence_packet_target_and_final_mapping_only",
}

COMPOSITION_REFINEMENT_AFTER_BASIS_QUERY_SUMMARY = (
    "when a later turn supplies concrete components or portions for the latest active meal after an "
    "estimate-basis inquiry, treat it as composition refinement after an estimate-basis inquiry: use "
    "correct_meal/correction_write, call estimate_nutrition, and do not answer_only or ask for replacement "
    "confirmation unless the user says it is a different meal; "
)

COMPOSITION_REFINEMENT_AFTER_BASIS_QUERY_EXAMPLE: dict[str, Any] = {
    "name": "composition_refinement_after_estimate_basis_query",
    "valid": {
        "manager_action": "call_tools",
        "tool_calls": [{"name": "estimate_nutrition"}],
        "evidence_posture": "evidence_pending",
        "semantic_decision": {
            "current_turn_intent": "correct_meal",
            "final_action_candidate": "correction_applied",
            "estimation_posture": "pending_tool_call",
            "mutation_intent_candidate": "correction_write",
        },
    },
    "invalid": {
        "manager_action": "final",
        "final_action": "answer_only",
        "workflow_effect": "answer_only",
        "semantic_decision": {
            "current_turn_intent": "answer_query",
            "mutation_intent_candidate": "no_mutation",
        },
    },
}

COMPOSITION_REFINEMENT_AFTER_BASIS_QUERY_DESCRIPTION = (
    "For composition refinement after an estimate-basis inquiry, use correct_meal/correction_write and call "
    "estimate_nutrition; do not answer_only or ask for replacement confirmation unless the user says it is a "
    "different meal. "
)


__all__ = [
    "COMPOSITION_REFINEMENT_AFTER_BASIS_QUERY_DESCRIPTION",
    "COMPOSITION_REFINEMENT_AFTER_BASIS_QUERY_EXAMPLE",
    "COMPOSITION_REFINEMENT_AFTER_BASIS_QUERY_RULE",
    "COMPOSITION_REFINEMENT_AFTER_BASIS_QUERY_SUMMARY",
]
