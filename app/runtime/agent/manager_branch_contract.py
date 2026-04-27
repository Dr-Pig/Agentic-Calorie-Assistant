from __future__ import annotations

from copy import deepcopy
import json
from typing import Any


B1_COMPOSITION_UNKNOWN_CASE_FAMILY = "composition_unknown_self_selected_basket"
B1_COMMON_FOOD_ITEM_CASE_FAMILY = "common_food_item"
B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY = "common_commercial_drink"
B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY = "common_commercial_meal"
B1_LISTED_INGREDIENT_CASE_FAMILY = "listed_ingredient_basket"
MANAGER_OUTPUT_CONTRACT_VIOLATION = "manager_output_contract_violation"
CLARIFICATION_BRANCH_CONFLICTING_FIELDS = "clarification_branch_conflicting_fields"
TOOL_CALL_BRANCH_CONFLICTING_FIELDS = "tool_call_branch_conflicting_fields"


class ManagerPass1BranchContractError(RuntimeError):
    def __init__(
        self,
        *,
        message: str,
        violation_family: str,
        actual_shape: str,
        conflicting_fields: list[str],
        observed_value: dict[str, Any],
        failing_component: str = "manager_branch_contract.validate_manager_pass1_branch",
    ) -> None:
        super().__init__(message)
        self.failure_family = MANAGER_OUTPUT_CONTRACT_VIOLATION
        self.violation_family = violation_family
        self.actual_shape = actual_shape
        self.conflicting_fields = list(conflicting_fields)
        self.failing_component = failing_component
        self.observed_value = observed_value
        rendered = json.dumps(observed_value, ensure_ascii=False, default=str)
        self.observed_type = "object"
        self.value_excerpt = rendered[:1200]
        self.value_truncated = len(rendered) > 1200


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
    manager_action = str(payload.get("manager_action") or "")
    response_mode = str(payload.get("response_mode") or "")
    final_action = str(payload.get("final_action") or "")
    workflow_effect = str(payload.get("workflow_effect") or "")
    uncertainty_posture = str(payload.get("uncertainty_posture") or "")
    tool_call_names = _tool_call_names(payload)
    conflicting_fields: list[str] = []
    if manager_action != "final":
        conflicting_fields.append(f"manager_action={manager_action or 'missing'}")
    if response_mode != "clarification":
        conflicting_fields.append(f"response_mode={response_mode or 'missing'}")
    if final_action != "request_clarification":
        conflicting_fields.append(f"final_action={final_action or 'missing'}")
    if tool_call_names:
        conflicting_fields.extend(f"tool_call={name}" for name in tool_call_names)
    if workflow_effect:
        conflicting_fields.append(f"workflow_effect={workflow_effect}")
    if uncertainty_posture:
        conflicting_fields.append(f"uncertainty_posture={uncertainty_posture}")
    if _contains_any_key(payload, {"item_results", "kcal_range", "likely_kcal"}):
        conflicting_fields.append("estimate_fields_present")
    if bool(payload.get("mutation_intent")):
        conflicting_fields.append("mutation_intent=true")
    if conflicting_fields:
        actual_shape = _actual_shape(payload)
        raise ManagerPass1BranchContractError(
            message="Manager Pass 1 clarification branch emitted conflicting fields.",
            violation_family=CLARIFICATION_BRANCH_CONFLICTING_FIELDS,
            actual_shape=actual_shape,
            conflicting_fields=conflicting_fields,
            observed_value=payload,
        )


def _validate_b1_listed_ingredient_tool_call_branch(payload: dict[str, Any]) -> None:
    manager_action = str(payload.get("manager_action") or "")
    response_mode = str(payload.get("response_mode") or "")
    final_action = str(payload.get("final_action") or "")
    workflow_effect = str(payload.get("workflow_effect") or "")
    tool_call_names = _tool_call_names(payload)
    conflicting_fields: list[str] = []
    if manager_action != "call_tools":
        conflicting_fields.append(f"manager_action={manager_action or 'missing'}")
    if not response_mode:
        conflicting_fields.append("response_mode=missing")
    if final_action:
        conflicting_fields.append(f"final_action={final_action}")
    if workflow_effect in {"pass_to_next_round", "commit", "log_food", "log_consumption"}:
        conflicting_fields.append(f"workflow_effect={workflow_effect}")
    if not tool_call_names:
        conflicting_fields.append("tool_calls=missing_or_empty")
    if conflicting_fields:
        actual_shape = _actual_shape(payload)
        raise ManagerPass1BranchContractError(
            message="Manager Pass 1 listed-ingredient tool-call branch emitted conflicting fields.",
            violation_family=TOOL_CALL_BRANCH_CONFLICTING_FIELDS,
            actual_shape=actual_shape,
            conflicting_fields=conflicting_fields,
            observed_value=payload,
        )


def _validate_b1_generic_tool_call_branch(payload: dict[str, Any]) -> None:
    manager_action = str(payload.get("manager_action") or "")
    response_mode = str(payload.get("response_mode") or "")
    final_action = str(payload.get("final_action") or "")
    workflow_effect = str(payload.get("workflow_effect") or "")
    tool_call_names = _tool_call_names(payload)
    conflicting_fields: list[str] = []
    if manager_action != "call_tools":
        conflicting_fields.append(f"manager_action={manager_action or 'missing'}")
    if not response_mode:
        conflicting_fields.append("response_mode=missing")
    if final_action:
        conflicting_fields.append(f"final_action={final_action}")
    if workflow_effect in {"pass_to_next_round", "commit", "log_food", "log_consumption"}:
        conflicting_fields.append(f"workflow_effect={workflow_effect}")
    if not tool_call_names:
        conflicting_fields.append("tool_calls=missing_or_empty")
    operations = payload.get("operations")
    if isinstance(operations, list) and operations:
        conflicting_fields.append("operations=non_empty")
    if _contains_any_key(payload, {"item_results", "kcal_range", "likely_kcal"}):
        conflicting_fields.append("estimate_fields_present")
    if bool(payload.get("mutation_intent")):
        conflicting_fields.append("mutation_intent=true")
    if conflicting_fields:
        actual_shape = _actual_shape(payload)
        raise ManagerPass1BranchContractError(
            message="Manager Pass 1 generic tool-call branch emitted conflicting fields.",
            violation_family=TOOL_CALL_BRANCH_CONFLICTING_FIELDS,
            actual_shape=actual_shape,
            conflicting_fields=conflicting_fields,
            observed_value=payload,
        )


def _is_b1_clarification_branch_constraint(constraints: dict[str, Any] | None) -> bool:
    if not isinstance(constraints, dict):
        return False
    return (
        str(constraints.get("phase_b1_manager_role") or "") == "pass_1_tool_request"
        and str(constraints.get("phase_b1_pass1_mode") or "") == "natural_tool_selection_probe"
        and str(constraints.get("phase_b1_case_family") or "") == B1_COMPOSITION_UNKNOWN_CASE_FAMILY
    )


def _is_b1_listed_ingredient_tool_call_constraint(constraints: dict[str, Any] | None) -> bool:
    if not isinstance(constraints, dict):
        return False
    return (
        str(constraints.get("phase_b1_manager_role") or "") == "pass_1_tool_request"
        and str(constraints.get("phase_b1_pass1_mode") or "") == "natural_tool_selection_probe"
        and str(constraints.get("phase_b1_case_family") or "") == B1_LISTED_INGREDIENT_CASE_FAMILY
    )


def _is_b1_generic_tool_call_constraint(constraints: dict[str, Any] | None) -> bool:
    if not isinstance(constraints, dict):
        return False
    return (
        str(constraints.get("phase_b1_manager_role") or "") == "pass_1_tool_request"
        and str(constraints.get("phase_b1_pass1_mode") or "") == "natural_tool_selection_probe"
        and str(constraints.get("phase_b1_case_family") or "")
        in {
            B1_COMMON_FOOD_ITEM_CASE_FAMILY,
            B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
            B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
        }
    )


def should_attempt_b1_generic_pass1_structured_output_transport(constraints: dict[str, Any] | None) -> bool:
    if not isinstance(constraints, dict):
        return False
    return (
        str(constraints.get("phase_b1_manager_role") or "") == "pass_1_tool_request"
        and str(constraints.get("phase_b1_pass1_mode") or "") == "natural_tool_selection_probe"
        and str(constraints.get("phase_b1_case_family") or "")
        in {
            B1_COMMON_FOOD_ITEM_CASE_FAMILY,
            B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
        }
    )


def should_attempt_b1_common_commercial_meal_pass1_decision_transport(constraints: dict[str, Any] | None) -> bool:
    if not isinstance(constraints, dict):
        return False
    return (
        str(constraints.get("phase_b1_manager_role") or "") == "pass_1_tool_request"
        and str(constraints.get("phase_b1_pass1_mode") or "") == "natural_tool_selection_probe"
        and str(constraints.get("phase_b1_case_family") or "") == B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY
    )


def manager_pass1_decision_tool_arguments_schema_for_constraints(
    base_schema: dict[str, Any] | None,
    constraints: dict[str, Any] | None,
) -> dict[str, Any] | None:
    return manager_pass1_schema_for_constraints(base_schema, constraints)


def _is_b1_generic_pass2_constraint(constraints: dict[str, Any] | None) -> bool:
    if not isinstance(constraints, dict):
        return False
    return (
        str(constraints.get("phase_b1_manager_role") or "") == "pass_2_synthesis"
        and str(constraints.get("phase_b1_pass1_mode") or "") == "natural_tool_selection_probe"
        and str(constraints.get("phase_b1_case_family") or "")
        in {
            B1_COMMON_FOOD_ITEM_CASE_FAMILY,
            B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
        }
    )


def _is_b1_common_commercial_meal_pass2_constraint(constraints: dict[str, Any] | None) -> bool:
    if not isinstance(constraints, dict):
        return False
    return (
        str(constraints.get("phase_b1_manager_role") or "") == "pass_2_synthesis"
        and str(constraints.get("phase_b1_pass1_mode") or "") == "natural_tool_selection_probe"
        and str(constraints.get("phase_b1_case_family") or "") == B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY
    )


def _is_b1_listed_ingredient_pass2_constraint(constraints: dict[str, Any] | None) -> bool:
    if not isinstance(constraints, dict):
        return False
    return (
        str(constraints.get("phase_b1_manager_role") or "") == "pass_2_synthesis"
        and str(constraints.get("phase_b1_pass1_mode") or "") == "natural_tool_selection_probe"
        and str(constraints.get("phase_b1_case_family") or "") == B1_LISTED_INGREDIENT_CASE_FAMILY
    )


def _manager_item_results_schema() -> dict[str, Any]:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "food_name": {"type": "string"},
                "kcal_range": {
                    "type": "array",
                    "items": {"type": "number"},
                },
                "likely_kcal": {"type": "number"},
                "uncertainty": {"type": "string"},
                "evidence_used": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["food_name", "kcal_range", "likely_kcal", "uncertainty", "evidence_used"],
            "additionalProperties": False,
        },
    }


def _tool_call_names(payload: dict[str, Any]) -> list[str]:
    tool_calls = payload.get("tool_calls")
    if not isinstance(tool_calls, list):
        return []
    names: list[str] = []
    for item in tool_calls:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("tool_name") or "").strip()
            if name:
                names.append(name)
    return names


def _contains_any_key(value: Any, keys: set[str]) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                found.append(key)
            found.extend(_contains_any_key(item, keys))
    elif isinstance(value, list):
        for item in value:
            found.extend(_contains_any_key(item, keys))
    return sorted(set(found))


def _actual_shape(payload: dict[str, Any]) -> str:
    manager_action = str(payload.get("manager_action") or "")
    final_action = str(payload.get("final_action") or "")
    response_mode = str(payload.get("response_mode") or "")
    workflow_effect = str(payload.get("workflow_effect") or "")
    uncertainty_posture = str(payload.get("uncertainty_posture") or "")
    tool_call_names = _tool_call_names(payload)
    parts: list[str] = []
    if manager_action:
        parts.append(manager_action)
    if final_action:
        parts.append(final_action)
    if tool_call_names:
        parts.extend(tool_call_names)
    if response_mode:
        parts.append(f"response_mode={response_mode}")
    if workflow_effect:
        parts.append(f"workflow_effect={workflow_effect}")
    if uncertainty_posture:
        parts.append(f"uncertainty_posture={uncertainty_posture}")
    if _contains_any_key(payload, {"item_results", "kcal_range", "likely_kcal"}):
        parts.append("pass1_estimate_fields")
    return ".".join(parts) if parts else "empty"
