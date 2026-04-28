from __future__ import annotations

import json
from typing import Any

from .manager_branch_shapes import actual_shape, contains_any_key, manager_item_results_schema, tool_call_names

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


def validate_b1_clarification_branch(payload: dict[str, Any]) -> None:
    manager_action = str(payload.get("manager_action") or "")
    response_mode = str(payload.get("response_mode") or "")
    final_action = str(payload.get("final_action") or "")
    workflow_effect = str(payload.get("workflow_effect") or "")
    uncertainty_posture = str(payload.get("uncertainty_posture") or "")
    names = tool_call_names(payload)
    conflicting_fields: list[str] = []
    if manager_action != "final":
        conflicting_fields.append(f"manager_action={manager_action or 'missing'}")
    if response_mode != "clarification":
        conflicting_fields.append(f"response_mode={response_mode or 'missing'}")
    if final_action != "request_clarification":
        conflicting_fields.append(f"final_action={final_action or 'missing'}")
    if names:
        conflicting_fields.extend(f"tool_call={name}" for name in names)
    if workflow_effect:
        conflicting_fields.append(f"workflow_effect={workflow_effect}")
    if uncertainty_posture:
        conflicting_fields.append(f"uncertainty_posture={uncertainty_posture}")
    if contains_any_key(payload, {"item_results", "kcal_range", "likely_kcal"}):
        conflicting_fields.append("estimate_fields_present")
    if bool(payload.get("mutation_intent")):
        conflicting_fields.append("mutation_intent=true")
    if conflicting_fields:
        raise ManagerPass1BranchContractError(
            message="Manager Pass 1 clarification branch emitted conflicting fields.",
            violation_family=CLARIFICATION_BRANCH_CONFLICTING_FIELDS,
            actual_shape=actual_shape(payload),
            conflicting_fields=conflicting_fields,
            observed_value=payload,
        )


def validate_b1_listed_ingredient_tool_call_branch(payload: dict[str, Any]) -> None:
    _validate_tool_call_branch(
        payload,
        message="Manager Pass 1 listed-ingredient tool-call branch emitted conflicting fields.",
        include_estimate_field_check=False,
    )


def validate_b1_generic_tool_call_branch(payload: dict[str, Any]) -> None:
    _validate_tool_call_branch(
        payload,
        message="Manager Pass 1 generic tool-call branch emitted conflicting fields.",
        include_estimate_field_check=True,
    )


def _validate_tool_call_branch(
    payload: dict[str, Any],
    *,
    message: str,
    include_estimate_field_check: bool,
) -> None:
    manager_action = str(payload.get("manager_action") or "")
    response_mode = str(payload.get("response_mode") or "")
    final_action = str(payload.get("final_action") or "")
    workflow_effect = str(payload.get("workflow_effect") or "")
    names = tool_call_names(payload)
    conflicting_fields: list[str] = []
    if manager_action != "call_tools":
        conflicting_fields.append(f"manager_action={manager_action or 'missing'}")
    if not response_mode:
        conflicting_fields.append("response_mode=missing")
    if final_action:
        conflicting_fields.append(f"final_action={final_action}")
    if workflow_effect in {"pass_to_next_round", "commit", "log_food", "log_consumption"}:
        conflicting_fields.append(f"workflow_effect={workflow_effect}")
    if not names:
        conflicting_fields.append("tool_calls=missing_or_empty")
    operations = payload.get("operations")
    if include_estimate_field_check and isinstance(operations, list) and operations:
        conflicting_fields.append("operations=non_empty")
    if include_estimate_field_check and contains_any_key(payload, {"item_results", "kcal_range", "likely_kcal"}):
        conflicting_fields.append("estimate_fields_present")
    if include_estimate_field_check and bool(payload.get("mutation_intent")):
        conflicting_fields.append("mutation_intent=true")
    if conflicting_fields:
        raise ManagerPass1BranchContractError(
            message=message,
            violation_family=TOOL_CALL_BRANCH_CONFLICTING_FIELDS,
            actual_shape=actual_shape(payload),
            conflicting_fields=conflicting_fields,
            observed_value=payload,
        )


__all__ = [
    "CLARIFICATION_BRANCH_CONFLICTING_FIELDS",
    "MANAGER_OUTPUT_CONTRACT_VIOLATION",
    "ManagerPass1BranchContractError",
    "TOOL_CALL_BRANCH_CONFLICTING_FIELDS",
    "actual_shape",
    "contains_any_key",
    "manager_item_results_schema",
    "tool_call_names",
    "validate_b1_clarification_branch",
    "validate_b1_generic_tool_call_branch",
    "validate_b1_listed_ingredient_tool_call_branch",
]
