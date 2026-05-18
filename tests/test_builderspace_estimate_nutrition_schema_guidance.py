from __future__ import annotations

from app.providers.builderspace_founder_schema_guidance import (
    apply_founder_live_contract_schema_guidance,
)


def test_estimate_nutrition_schema_guidance_requires_manager_owned_target_shape() -> None:
    schema = {
        "properties": {
            "manager_action": {"type": "string"},
            "tool_calls": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "arguments": {"type": "object"},
                    },
                },
            },
            "semantic_decision": {"type": "object", "properties": {}},
        }
    }

    apply_founder_live_contract_schema_guidance(schema)

    estimate_rule = next(
        rule
        for rule in schema["properties"]["tool_calls"]["items"]["allOf"]
        if rule["if"]["properties"]["name"]["const"] == "estimate_nutrition"
    )
    manager_decision_schema = estimate_rule["then"]["properties"]["arguments"]["properties"][
        "manager_semantic_decision"
    ]

    assert manager_decision_schema["description"].startswith(
        "Manager-owned evidence target for estimate_nutrition"
    )
    assert {"required": ["base_dish"]} in manager_decision_schema["anyOf"]
    assert {"required": ["aliases"]} in manager_decision_schema["anyOf"]
    assert {"required": ["brand_hint", "size_hint"]} in manager_decision_schema["anyOf"]
    assert {"required": ["listed_items"]} in manager_decision_schema["anyOf"]
