from __future__ import annotations

from typing import Any

from ..runtime.agent.manager_branch_contract import (
    ManagerPass1BranchContractError,
    manager_pass1_schema_for_constraints,
    validate_manager_pass1_branch,
)
from ..runtime.agent.founder_live_manager_contract import (
    FOUNDER_LIVE_MANAGER_ALLOWED_FINAL_ACTIONS,
    FOUNDER_LIVE_MANAGER_ALLOWED_INTENT_TYPES,
    FOUNDER_LIVE_MANAGER_FIELD_CONSUMERS,
    FOUNDER_LIVE_MANAGER_REQUIRED_FIELDS,
    FOUNDER_LIVE_MANAGER_REPAIR_ALLOWED_TOOL_NAMES,
    FOUNDER_LIVE_MANAGER_REPAIR_REQUIRED_TOOL_BY_FAMILY,
    founder_live_manager_repair_failure_family,
    is_founder_live_manager_contract,
    validate_founder_live_manager_contract_consistency,
)
from ..runtime.agent.manager_branch_shapes import manager_semantic_decision_schema
from ..runtime.contracts.trace import MANAGER_LOOP_STAGE


def manager_loop_schema(constraints: dict[str, Any] | None = None) -> dict[str, Any]:
    base_schema = {
        "type": "object",
        "properties": {
            "manager_action": {"type": "string", "enum": ["call_tools", "final"]},
            "interaction_family": {"type": "string"},
            "response_mode": {"type": "string"},
            "intent": {"type": "string"},
            "intent_type": {"type": "string"},
            "workflow_effect": {"type": "string"},
            "target_attachment": {"type": "object"},
            "exactness": {"type": "string"},
            "confidence": {"type": "string"},
            "evidence_posture": {"type": "string"},
            "repair_ack": {"type": "boolean"},
            "response_summary": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "pending_followup": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "tool_calls": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "arguments": {"type": "object"},
                    },
                    "required": ["name"],
                    "additionalProperties": False,
                },
            },
            "final_action": {"type": "string"},
            "operations": {"type": "array"},
            "answer_contract": {"type": "object"},
            "uncertainty_posture": {"type": "string"},
            "evidence_honesty_posture": {"type": "string"},
            "semantic_decision": manager_semantic_decision_schema(),
        },
        "required": [
            "manager_action",
            "intent",
            "workflow_effect",
            "target_attachment",
            "exactness",
            "confidence",
            "evidence_posture",
            "repair_ack",
        ],
        "additionalProperties": False,
    }
    if is_founder_live_manager_contract(constraints):
        repair_failure_family = founder_live_manager_repair_failure_family(constraints)
        required_repair_tool = FOUNDER_LIVE_MANAGER_REPAIR_REQUIRED_TOOL_BY_FAMILY.get(repair_failure_family)
        base_schema["properties"]["intent_type"] = {
            "type": "string",
            "enum": list(FOUNDER_LIVE_MANAGER_ALLOWED_INTENT_TYPES),
        }
        base_schema["properties"]["final_action"] = {
            "type": "string",
            "enum": list(FOUNDER_LIVE_MANAGER_ALLOWED_FINAL_ACTIONS),
        }
        if required_repair_tool:
            base_schema["properties"]["manager_action"] = {"type": "string", "enum": ["call_tools"]}
            base_schema["properties"]["tool_calls"] = {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "enum": list(FOUNDER_LIVE_MANAGER_REPAIR_ALLOWED_TOOL_NAMES)},
                        "arguments": {"type": "object"},
                    },
                    "required": ["name"],
                    "additionalProperties": False,
                },
            }
            base_schema["x-repair-contract"] = {
                "failure_family": repair_failure_family,
                "required_tool": required_repair_tool,
            }
            base_schema["required"] = [*FOUNDER_LIVE_MANAGER_REQUIRED_FIELDS, "tool_calls"]
            base_schema["x-field-consumers"] = dict(FOUNDER_LIVE_MANAGER_FIELD_CONSUMERS)
            return base_schema
        base_schema["required"] = list(FOUNDER_LIVE_MANAGER_REQUIRED_FIELDS)
        base_schema["x-field-consumers"] = dict(FOUNDER_LIVE_MANAGER_FIELD_CONSUMERS)
        return base_schema
    return manager_pass1_schema_for_constraints(base_schema, constraints)


def response_schema_for_stage(stage: str, constraints: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if stage == MANAGER_LOOP_STAGE:
        return manager_loop_schema(constraints)
    return None


def validate_manager_payload(stage: str, payload: dict[str, Any], *, constraints: dict[str, Any] | None = None) -> None:
    schema = response_schema_for_stage(stage, constraints)
    if schema is None:
        return
    required = set(schema.get("required") or [])
    missing = sorted(key for key in required if key not in payload)
    if missing:
        raise RuntimeError(f"manager payload missing required fields for {stage}: {missing}")
    if schema.get("additionalProperties") is False:
        allowed = set((schema.get("properties") or {}).keys())
        unknown = sorted(key for key in payload.keys() if key not in allowed)
        if unknown:
            raise RuntimeError(f"manager payload has unknown fields for {stage}: {unknown}")
    if stage == MANAGER_LOOP_STAGE:
        validate_manager_pass1_branch(payload, constraints)
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    for key, spec in properties.items():
        if not isinstance(spec, dict) or "enum" not in spec or key not in payload:
            continue
        allowed_values = set(spec.get("enum") or [])
        if payload.get(key) not in allowed_values:
            raise RuntimeError(f"manager payload field {key} invalid for {stage}: {payload.get(key)!r}")
    if is_founder_live_manager_contract(constraints):
        validate_founder_live_manager_contract_consistency(payload, constraints=constraints)


__all__ = [
    "ManagerPass1BranchContractError",
    "manager_loop_schema",
    "response_schema_for_stage",
    "validate_manager_payload",
]
