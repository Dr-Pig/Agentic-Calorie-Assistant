from __future__ import annotations

from app.providers.builderspace_contract_repair import contract_repair_message


def test_target_ambiguity_repair_message_allows_target_clarification() -> None:
    message = contract_repair_message(
        {
            "error": (
                "founder live manager contract ambiguous correction target requires "
                "final ask_followup target clarification"
            ),
            "observed_value": {
                "target_attachment": {"meal_thread_id": 2},
                "semantic_decision": {"current_turn_intent": "correct_meal"},
            },
        }
    )

    assert "CONTRACT_REPAIR" in message
    assert "ask the user to clarify the target" in message
    assert "Do not preserve the rejected target_attachment" in message
    assert "Do not change user intent, target_attachment" not in message
