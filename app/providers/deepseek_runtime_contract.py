from __future__ import annotations

from typing import Any

from ..runtime.agent.manager_branch_contract import (
    ManagerPass1BranchContractError,
    manager_pass1_schema_for_constraints,
    should_attempt_b1_generic_pass1_structured_output_transport,
    validate_manager_pass1_branch,
)
from ..runtime.agent.manager_branch_shapes import manager_semantic_decision_schema
from ..runtime.contracts.trace import MANAGER_LOOP_STAGE


def response_schema_for_stage(stage: str, constraints: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if stage == MANAGER_LOOP_STAGE:
        base_schema = {
            "type": "object",
            "properties": {
                "manager_action": {"type": "string"},
                "interaction_family": {"type": "string"},
                "response_mode": {"type": "string"},
                "intent": {"type": "string"},
                "intent_type": {"type": "string"},
                "final_action": {"type": "string"},
                "workflow_effect": {"type": "string"},
                "target_attachment": {"type": "object"},
                "exactness": {"type": "string"},
                "confidence": {"type": "string"},
                "evidence_posture": {"type": "string"},
                "repair_ack": {"type": "boolean"},
                "answer_contract": {"type": "object"},
                "uncertainty_posture": {"type": "string"},
                "evidence_honesty_posture": {"type": "string"},
                "semantic_decision": manager_semantic_decision_schema(),
                "response_summary": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "pending_followup": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "tool_calls": {
                    "type": "array",
                    "items": {"type": "object", "properties": {"name": {"type": "string"}, "arguments": {"type": "object"}}, "required": ["name"], "additionalProperties": False},
                },
                "operations": {"type": "array"},
            },
            "required": ["manager_action", "intent", "workflow_effect", "target_attachment", "exactness", "confidence", "evidence_posture", "repair_ack"],
            "additionalProperties": False,
        }
        return manager_pass1_schema_for_constraints(base_schema, constraints)
    return None


def response_format_request_for_stage(stage: str, *, constraints: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    constraint_snapshot = {
        "phase_b1_manager_role": str((constraints or {}).get("phase_b1_manager_role") or ""),
        "phase_b1_pass1_mode": str((constraints or {}).get("phase_b1_pass1_mode") or ""),
        "phase_b1_case_family": str((constraints or {}).get("phase_b1_case_family") or ""),
    }
    if stage == MANAGER_LOOP_STAGE and should_attempt_b1_generic_pass1_structured_output_transport(constraints):
        schema = response_schema_for_stage(stage, constraints)
        return (
            {"type": "json_schema", "json_schema": {"name": "phase_b1_generic_pass1_call_tools", "strict": True, "schema": schema}},
            {
                "structured_output_transport_attempted": True,
                "structured_output_transport_mode": "json_schema",
                "structured_output_transport_accepted": True,
                "structured_output_transport_fallback": None,
                "fallback_reason": None,
                "structured_output_transport_constraint_snapshot": constraint_snapshot,
            },
        )
    return (
        {"type": "json_object"},
        {
            "structured_output_transport_attempted": False,
            "structured_output_transport_mode": "json_object",
            "structured_output_transport_accepted": False,
            "structured_output_transport_fallback": None,
            "fallback_reason": None,
            "structured_output_transport_constraint_snapshot": constraint_snapshot,
        },
    )


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


__all__ = ["ManagerPass1BranchContractError", "response_schema_for_stage", "response_format_request_for_stage", "validate_manager_payload"]
