from __future__ import annotations

from typing import Any

from ..runtime.agent.manager_branch_contract import (
    ManagerPass1BranchContractError,
    manager_pass1_schema_for_constraints,
    validate_manager_pass1_branch,
)
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


__all__ = [
    "ManagerPass1BranchContractError",
    "manager_loop_schema",
    "response_schema_for_stage",
    "validate_manager_payload",
]
