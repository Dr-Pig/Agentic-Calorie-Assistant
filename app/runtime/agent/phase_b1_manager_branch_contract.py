from __future__ import annotations

from typing import Any

from copy import deepcopy

from .manager_branch_constraints import (
    is_b1_clarification_branch_constraint as _is_b1_clarification_branch_constraint,
    is_b1_clarification_pass2_constraint as _is_b1_clarification_pass2_constraint,
    is_b1_common_commercial_meal_pass2_constraint as _is_b1_common_commercial_meal_pass2_constraint,
    is_b1_forced_tool_request_constraint as _is_b1_forced_tool_request_constraint,
    is_b1_generic_pass2_constraint as _is_b1_generic_pass2_constraint,
    is_b1_generic_tool_call_constraint as _is_b1_generic_tool_call_constraint,
    is_b1_listed_ingredient_pass2_constraint as _is_b1_listed_ingredient_pass2_constraint,
    is_b1_listed_ingredient_tool_call_constraint as _is_b1_listed_ingredient_tool_call_constraint,
)
from .manager_branch_shapes import (
    manager_item_results_schema as _manager_item_results_schema,
    manager_semantic_decision_schema as _manager_semantic_decision_schema,
)
from .manager_branch_validation import (
    validate_b1_clarification_branch as _delegate_validate_b1_clarification_branch,
    validate_b1_clarification_pass2_branch as _delegate_validate_b1_clarification_pass2_branch,
    validate_b1_generic_tool_call_branch as _delegate_validate_b1_generic_tool_call_branch,
    validate_b1_listed_ingredient_tool_call_branch as _delegate_validate_b1_listed_ingredient_tool_call_branch,
)


_B1_CANONICAL_READ_TOOL_NAMES = [
    "lookup_generic_food",
    "retrieve_web_food_evidence",
    "load_taiwan_food_semantics_skill",
]


def manager_pass1_schema_for_constraints(
    base_schema: dict[str, Any] | None,
    constraints: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if base_schema is None:
        return None
    schema = deepcopy(base_schema)
    properties = schema.setdefault("properties", {})
    properties.setdefault("interaction_family", {"type": "string"})
    properties.setdefault("response_mode", {"type": "string"})
    properties.setdefault("operations", {"type": "array"})
    properties.setdefault("answer_contract", {"type": "object"})
    properties.setdefault("semantic_decision", _manager_semantic_decision_schema())
    if _is_b1_clarification_pass2_constraint(constraints):
        allowed_keys = {
            "manager_action",
            "interaction_family",
            "response_mode",
            "intent",
            "workflow_effect",
            "target_attachment",
            "final_action",
            "exactness",
            "confidence",
            "evidence_posture",
            "repair_ack",
            "response_summary",
            "pending_followup",
            "operations",
            "answer_contract",
            "item_results",
            "evidence_used",
            "uncertainty_posture",
            "evidence_honesty_posture",
            "semantic_decision",
        }
        schema["properties"] = {key: value for key, value in properties.items() if key in allowed_keys}
        schema["properties"]["manager_action"] = {"type": "string", "enum": ["final"]}
        schema["properties"]["response_mode"] = {"type": "string", "enum": ["clarification"]}
        schema["properties"]["final_action"] = {"type": "string", "enum": ["request_clarification"]}
        schema["properties"]["workflow_effect"] = {"type": "string", "enum": ["pause_for_clarification", "none"]}
        schema["properties"]["uncertainty_posture"] = {
            "type": "string",
            "enum": ["composition_unknown_basket", "none"],
        }
        schema["properties"]["item_results"] = _manager_item_results_schema()
        schema["properties"]["evidence_used"] = {
            "type": "array",
            "items": {"type": "string"},
        }
        schema["required"] = [
            "manager_action",
            "response_mode",
            "intent",
            "workflow_effect",
            "target_attachment",
            "final_action",
            "exactness",
            "confidence",
            "evidence_posture",
            "repair_ack",
            "operations",
            "answer_contract",
        ]
        return schema
    if _is_b1_common_commercial_meal_pass2_constraint(constraints):
        allowed_keys = {
            "manager_action",
            "interaction_family",
            "response_mode",
            "intent",
            "workflow_effect",
            "target_attachment",
            "final_action",
            "exactness",
            "confidence",
            "evidence_posture",
            "repair_ack",
            "response_summary",
            "pending_followup",
            "operations",
            "answer_contract",
            "item_results",
            "evidence_used",
            "uncertainty_posture",
            "evidence_honesty_posture",
            "semantic_decision",
        }
        schema["properties"] = {key: value for key, value in properties.items() if key in allowed_keys}
        schema["properties"]["manager_action"] = {"type": "string", "enum": ["final"]}
        schema["properties"]["item_results"] = _manager_item_results_schema()
        schema["properties"]["evidence_used"] = {
            "type": "array",
            "items": {"type": "string"},
        }
        schema["required"] = [
            "manager_action",
            "response_mode",
            "intent",
            "workflow_effect",
            "target_attachment",
            "exactness",
            "confidence",
            "evidence_posture",
            "repair_ack",
            "item_results",
            "operations",
            "answer_contract",
        ]
        return schema
    if _is_b1_generic_pass2_constraint(constraints):
        allowed_keys = {
            "manager_action",
            "interaction_family",
            "response_mode",
            "intent",
            "workflow_effect",
            "target_attachment",
            "final_action",
            "exactness",
            "confidence",
            "evidence_posture",
            "repair_ack",
            "response_summary",
            "pending_followup",
            "operations",
            "answer_contract",
            "item_results",
            "evidence_used",
            "uncertainty_posture",
            "evidence_honesty_posture",
            "semantic_decision",
        }
        schema["properties"] = {key: value for key, value in properties.items() if key in allowed_keys}
        schema["properties"]["manager_action"] = {"type": "string", "enum": ["final"]}
        schema["properties"]["item_results"] = _manager_item_results_schema()
        schema["properties"]["evidence_used"] = {
            "type": "array",
            "items": {"type": "string"},
        }
        schema["required"] = [
            "manager_action",
            "response_mode",
            "intent",
            "workflow_effect",
            "target_attachment",
            "exactness",
            "confidence",
            "evidence_posture",
            "repair_ack",
            "operations",
            "answer_contract",
        ]
        return schema
    if _is_b1_listed_ingredient_pass2_constraint(constraints):
        allowed_keys = {
            "manager_action",
            "interaction_family",
            "response_mode",
            "intent",
            "workflow_effect",
            "target_attachment",
            "exactness",
            "confidence",
            "evidence_posture",
            "repair_ack",
            "item_results",
            "operations",
            "answer_contract",
            "semantic_decision",
        }
        schema["properties"] = {key: value for key, value in properties.items() if key in allowed_keys}
        schema["properties"]["manager_action"] = {"type": "string", "enum": ["final"]}
        schema["properties"]["item_results"] = _manager_item_results_schema()
        schema["required"] = [
            "manager_action",
            "response_mode",
            "intent",
            "workflow_effect",
            "target_attachment",
            "exactness",
            "confidence",
            "evidence_posture",
            "repair_ack",
            "item_results",
            "operations",
            "answer_contract",
        ]
        return schema
    if _is_b1_forced_tool_request_constraint(constraints):
        _apply_b1_tool_call_contract(properties)
        schema["properties"] = properties
        schema["required"] = _b1_tool_call_required_fields()
        return schema
    if _is_b1_generic_tool_call_constraint(constraints):
        _apply_b1_tool_call_contract(properties)
        properties["manager_action"] = {"type": "string", "enum": ["call_tools"]}
        properties["operations"] = {"type": "array", "maxItems": 0}
        schema["required"] = _b1_tool_call_required_fields()
        return schema
    if _is_b1_listed_ingredient_tool_call_constraint(constraints):
        _apply_b1_tool_call_contract(properties)
        properties["manager_action"] = {"type": "string", "enum": ["call_tools"]}
        properties["operations"] = {"type": "array", "maxItems": 0}
        schema["required"] = _b1_tool_call_required_fields()
        return schema
    if not _is_b1_clarification_branch_constraint(constraints):
        return schema
    properties["manager_action"] = {"type": "string", "enum": ["final"]}
    properties["response_mode"] = {"type": "string", "enum": ["clarification"]}
    properties["final_action"] = {"type": "string", "enum": ["request_clarification"]}
    properties["operations"] = {"type": "array", "maxItems": 0}
    required = [
        "manager_action",
        "response_mode",
        "final_action",
        "operations",
        "answer_contract",
    ]
    schema["required"] = required
    return schema


def _apply_b1_tool_call_contract(properties: dict[str, Any]) -> None:
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


def _b1_tool_call_required_fields() -> list[str]:
    return [
        "manager_action",
        "response_mode",
        "operations",
        "answer_contract",
        "tool_calls",
    ]


def validate_manager_pass1_branch(payload: dict[str, Any], constraints: dict[str, Any] | None) -> None:
    if _is_b1_forced_tool_request_constraint(constraints):
        _validate_b1_generic_tool_call_branch(payload)
        return
    if _is_b1_clarification_pass2_constraint(constraints):
        _validate_b1_clarification_pass2_branch(payload)
        return
    if _is_b1_common_commercial_meal_pass2_constraint(constraints):
        return
    if _is_b1_generic_pass2_constraint(constraints):
        return
    if _is_b1_listed_ingredient_pass2_constraint(constraints):
        return
    if _is_b1_generic_tool_call_constraint(constraints):
        _validate_b1_generic_tool_call_branch(payload)
        return
    if _is_b1_listed_ingredient_tool_call_constraint(constraints):
        _validate_b1_listed_ingredient_tool_call_branch(payload)
        return
    if not _is_b1_clarification_branch_constraint(constraints):
        return
    _validate_b1_clarification_branch(payload)


def _validate_b1_clarification_branch(payload: dict[str, Any]) -> None:
    _delegate_validate_b1_clarification_branch(payload)


def _validate_b1_clarification_pass2_branch(payload: dict[str, Any]) -> None:
    _delegate_validate_b1_clarification_pass2_branch(payload)


def _validate_b1_listed_ingredient_tool_call_branch(payload: dict[str, Any]) -> None:
    _delegate_validate_b1_listed_ingredient_tool_call_branch(payload)


def _validate_b1_generic_tool_call_branch(payload: dict[str, Any]) -> None:
    _delegate_validate_b1_generic_tool_call_branch(payload)


def manager_pass1_decision_tool_arguments_schema_for_constraints(
    base_schema: dict[str, Any] | None,
    constraints: dict[str, Any] | None,
) -> dict[str, Any] | None:
    return manager_pass1_schema_for_constraints(base_schema, constraints)
