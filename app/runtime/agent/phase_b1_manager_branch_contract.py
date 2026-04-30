from __future__ import annotations

from typing import Any

from copy import deepcopy

from .manager_branch_constraints import (
    B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
    B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
    B1_COMMON_FOOD_ITEM_CASE_FAMILY,
    B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
    B1_LISTED_INGREDIENT_CASE_FAMILY,
    is_b1_clarification_branch_constraint as _is_b1_clarification_branch_constraint,
    is_b1_clarification_pass2_constraint as _is_b1_clarification_pass2_constraint,
    is_b1_common_commercial_meal_pass2_constraint as _is_b1_common_commercial_meal_pass2_constraint,
    is_b1_generic_pass2_constraint as _is_b1_generic_pass2_constraint,
    is_b1_generic_tool_call_constraint as _is_b1_generic_tool_call_constraint,
    is_b1_listed_ingredient_pass2_constraint as _is_b1_listed_ingredient_pass2_constraint,
    is_b1_listed_ingredient_tool_call_constraint as _is_b1_listed_ingredient_tool_call_constraint,
    should_attempt_b1_common_commercial_meal_pass1_decision_transport,
    should_attempt_b1_generic_pass1_structured_output_transport,
)
from .manager_branch_shapes import (
    manager_item_results_schema as _manager_item_results_schema,
    manager_semantic_decision_schema as _manager_semantic_decision_schema,
)
from .manager_branch_validation import (
    CLARIFICATION_BRANCH_CONFLICTING_FIELDS,
    ManagerPass1BranchContractError,
    MANAGER_OUTPUT_CONTRACT_VIOLATION,
    TOOL_CALL_BRANCH_CONFLICTING_FIELDS,
    validate_b1_clarification_branch as _delegate_validate_b1_clarification_branch,
    validate_b1_clarification_pass2_branch as _delegate_validate_b1_clarification_pass2_branch,
    validate_b1_generic_tool_call_branch as _delegate_validate_b1_generic_tool_call_branch,
    validate_b1_listed_ingredient_tool_call_branch as _delegate_validate_b1_listed_ingredient_tool_call_branch,
)


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
        schema["properties"]["item_results"] = _manager_item_results_schema()
        schema["properties"]["evidence_used"] = {
            "type": "array",
            "items": {"type": "string"},
        }
        schema["required"] = [
            "manager_action",
            "response_mode",
            "final_action",
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
    if _is_b1_generic_tool_call_constraint(constraints):
        properties["manager_action"] = {"type": "string", "enum": ["call_tools"]}
        properties["operations"] = {"type": "array", "maxItems": 0}
        required = [
            "manager_action",
            "response_mode",
            "operations",
            "answer_contract",
            "tool_calls",
        ]
        schema["required"] = required
        return schema
    if _is_b1_listed_ingredient_tool_call_constraint(constraints):
        properties["manager_action"] = {"type": "string", "enum": ["call_tools"]}
        properties["operations"] = {"type": "array", "maxItems": 0}
        required = [
            "manager_action",
            "response_mode",
            "operations",
            "answer_contract",
            "tool_calls",
        ]
        schema["required"] = required
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


def validate_manager_pass1_branch(payload: dict[str, Any], constraints: dict[str, Any] | None) -> None:
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
