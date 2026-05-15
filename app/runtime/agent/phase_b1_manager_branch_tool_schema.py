from __future__ import annotations

from typing import Any

_B1_CANONICAL_READ_TOOL_NAMES = [
    "lookup_generic_food",
    "retrieve_web_food_evidence",
    "load_taiwan_food_semantics_skill",
]


def apply_b1_tool_call_contract(properties: dict[str, Any]) -> None:
    properties["manager_action"] = {"type": "string", "enum": ["call_tools"]}
    properties["operations"] = {"type": "array", "maxItems": 0}
    properties["tool_calls"] = {
        "type": "array",
        "minItems": 1,
        "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "enum": _B1_CANONICAL_READ_TOOL_NAMES},
                "arguments": {"type": "object"},
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    }


def b1_tool_call_required_fields() -> list[str]:
    return [
        "manager_action",
        "response_mode",
        "operations",
        "answer_contract",
        "tool_calls",
    ]


__all__ = ["apply_b1_tool_call_contract", "b1_tool_call_required_fields"]
