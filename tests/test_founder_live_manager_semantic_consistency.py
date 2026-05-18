from __future__ import annotations

import pytest

from app.runtime.agent.founder_live_manager_semantic_consistency import (
    validate_semantic_field_consistency,
)


def _payload_with_required_slot_update(*, final_action: str, mutation_intent: str) -> dict[str, object]:
    return {
        "manager_action": "final",
        "final_action": final_action,
        "workflow_effect": final_action,
        "semantic_decision": {
            "current_turn_intent": "log_meal",
            "retrieval_goal": "listed_item_lookup",
            "listed_items": [
                "\u9435\u677f\u9eb5",
                "\u8c6c\u8089\u7247",
                "\u8377\u5305\u86cb",
                "\u7d05\u8336",
            ],
            "final_action_candidate": final_action,
            "mutation_intent_candidate": mutation_intent,
            "active_workflow_resolution": {
                "current_turn_relation": "answers_optional_slot",
                "slot_updates": [
                    {
                        "slot_id": "composition_details",
                        "slot_kind": "composition_items",
                        "required_for_commit": True,
                        "current_value": "teppan,pork,egg,tea",
                        "source": "current_turn",
                        "resolution_condition": "user supplied listed components",
                        "asked_question": "Which items and portions should I estimate?",
                    }
                ],
                "still_missing_slots": [
                    {
                        "slot_id": "portion_amount",
                        "slot_kind": "portion_amount",
                        "required_for_commit": False,
                        "missing_reason": "portion can refine estimate later",
                    }
                ],
                "attach_target": {"operation": "attach_to_pending_followup"},
                "final_action": final_action,
                "resolution_basis": ["current_turn", "pending_followup"],
                "selection_owner": "manager",
                "deterministic_role": "validate_only",
            },
        },
    }


def test_optional_only_missing_slots_cannot_downgrade_to_followup_after_required_slot_update() -> None:
    payload = _payload_with_required_slot_update(
        final_action="ask_followup",
        mutation_intent="no_mutation",
    )

    with pytest.raises(RuntimeError, match="only optional missing slots"):
        validate_semantic_field_consistency(payload)


def test_optional_only_missing_slots_allow_commit_after_required_slot_update() -> None:
    payload = _payload_with_required_slot_update(
        final_action="commit",
        mutation_intent="canonical_write",
    )

    validate_semantic_field_consistency(payload)
