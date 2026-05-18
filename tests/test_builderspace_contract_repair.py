from __future__ import annotations

from app.providers.builderspace_contract_repair import contract_repair_message


def test_target_ambiguity_repair_message_allows_target_clarification() -> None:
    message = contract_repair_message(
        {
            "error": (
                "founder live manager contract ambiguous correction target requires "
                "Manager target retry or final ask_followup"
            ),
            "observed_value": {
                "target_attachment": {"meal_thread_id": 2},
                "semantic_decision": {"current_turn_intent": "correct_meal"},
            },
        }
    )

    assert "CONTRACT_REPAIR" in message
    assert "If the current turn uniquely identifies one candidate" in message
    assert "resolve_correction_target" in message
    assert "ask the user to clarify the target" in message
    assert "Do not preserve the rejected target_attachment" in message
    assert "Do not change user intent, target_attachment" not in message


def test_repeated_nutrition_evidence_repair_message_requires_final_mapping() -> None:
    message = contract_repair_message(
        {
            "error": (
                "founder live manager contract nutrition evidence already present; "
                "return manager_action='final'"
            ),
            "observed_value": {
                "manager_action": "call_tools",
                "tool_calls": [{"name": "estimate_nutrition"}],
                "semantic_decision": {"current_turn_intent": "correct_meal"},
            },
        }
    )

    assert "CONTRACT_REPAIR" in message
    assert "nutrition evidence is already present" in message
    assert "manager_action='final'" in message
    assert "Do not call estimate_nutrition again" in message
    assert "Do not change user intent" in message


def test_unselected_target_repair_message_requires_manager_selected_candidate() -> None:
    message = contract_repair_message(
        {
            "error": "founder live manager contract resolve_correction_target requires Manager-selected target argument",
            "observed_value": {
                "manager_action": "call_tools",
                "tool_calls": [
                    {
                        "name": "resolve_correction_target",
                        "arguments": {"user_input": "delete breakfast", "target_candidates": []},
                    }
                ],
            },
        }
    )

    assert "CONTRACT_REPAIR" in message
    assert "select one target from context candidates" in message
    assert "meal_thread_id" in message
    assert "早餐, 午餐, 中餐, 晚餐, or 宵夜" in message
    assert "candidate meal_thread_id and target_display_name" in message
    assert "do not pass target_candidates" in message


def test_targetless_estimate_repair_message_requires_manager_owned_evidence_target() -> None:
    message = contract_repair_message(
        {
            "error": (
                "founder live manager contract estimate_nutrition requires Manager-owned "
                "evidence target"
            ),
            "observed_value": {
                "manager_action": "call_tools",
                "tool_calls": [{"name": "estimate_nutrition", "arguments": {}}],
            },
        }
    )

    assert "CONTRACT_REPAIR" in message
    assert "estimate_nutrition requires a Manager-owned evidence target" in message
    assert "base_dish" in message
    assert "multiple listed_items" in message
    assert "ask a follow-up" in message
    assert "Runtime must not infer the target from raw user text" in message
