from __future__ import annotations

import pytest

from app.runtime.agent.founder_live_manager_tool_call_contract import (
    validate_tool_call_contracts,
)


def test_estimate_nutrition_requires_manager_owned_evidence_target() -> None:
    payload = {
        "manager_action": "call_tools",
        "tool_calls": [
            {
                "name": "estimate_nutrition",
                "arguments": {
                    "manager_semantic_decision": {
                        "retrieval_goal": "generic_anchor_lookup",
                        "semantic_authority_source": "live_manager_structured_output",
                    }
                },
            }
        ],
    }

    with pytest.raises(RuntimeError, match="requires Manager-owned evidence target"):
        validate_tool_call_contracts(payload, evidence_state={})


def test_estimate_nutrition_accepts_manager_owned_base_dish_target() -> None:
    payload = {
        "manager_action": "call_tools",
        "tool_calls": [
            {
                "name": "estimate_nutrition",
                "arguments": {
                    "manager_semantic_decision": {
                        "base_dish": "chicken rice",
                        "retrieval_goal": "generic_anchor_lookup",
                        "semantic_authority_source": "live_manager_structured_output",
                    }
                },
            }
        ],
    }

    validate_tool_call_contracts(payload, evidence_state={})


def test_estimate_nutrition_accepts_manager_owned_component_targets() -> None:
    payload = {
        "manager_action": "call_tools",
        "tool_calls": [
            {
                "name": "estimate_nutrition",
                "arguments": {
                    "manager_semantic_decision": {
                        "listed_items": ["teppan noodles", "egg", "pork slices"],
                        "retrieval_goal": "listed_item_lookup",
                        "semantic_authority_source": "live_manager_structured_output",
                    }
                },
            }
        ],
    }

    validate_tool_call_contracts(payload, evidence_state={})
