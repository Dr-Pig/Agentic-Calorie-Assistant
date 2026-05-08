from __future__ import annotations

from typing import Any

from ..runtime.agent.manager_branch_contract import (
    ManagerPass1BranchContractError,
    manager_pass1_schema_for_constraints,
    validate_manager_pass1_branch,
)
from .builderspace_final_mapping_schema import apply_evidence_present_final_mapping_schema
from ..runtime.agent.founder_live_manager_contract import (
    FOUNDER_LIVE_MANAGER_ALLOWED_FINAL_ACTIONS,
    FOUNDER_LIVE_MANAGER_ALLOWED_INTENT_TYPES,
    FOUNDER_LIVE_MANAGER_CALL_TOOLS_FINAL_ACTIONS,
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


def _apply_founder_live_contract_schema_guidance(base_schema: dict[str, Any]) -> None:
    properties = base_schema.get("properties")
    if not isinstance(properties, dict):
        return
    manager_action = properties.get("manager_action")
    if isinstance(manager_action, dict):
        manager_action["description"] = (
            "Use call_tools when current-loop evidence is still required. If "
            "semantic_decision.final_action_candidate is commit, correction_applied, or overshoot_note "
            "and manager_contract_evidence_state.nutrition_evidence_present is false, this field must be "
            "call_tools with estimate_nutrition; do not return final with ask_followup, answer_only, or no_commit "
            "as a substitute. If evidence_posture says requires_tool/evidence_missing/evidence_pending or "
            "semantic_decision.estimation_posture says pending_tool_call/tool_pending, this field must be call_tools. "
            "Exception: explicit remove_item correction uses target evidence from resolve_correction_target, not estimate_nutrition. "
            "If target_evidence_present is true with target_evidence_operation remove_item, return final correction_applied and do not call resolve_correction_target again. Exception: composition-unknown baskets are not tool evidence missing; return final "
            "ask_followup with tool_calls=[] instead of call_tools; manager_action=call_tools is invalid for composition-unknown "
            "baskets. Every call_tools response must include a non-empty "
            "tool_calls array."
        )
    evidence_posture = properties.get("evidence_posture")
    if isinstance(evidence_posture, dict):
        evidence_posture["description"] = (
            "Evidence status for this manager round. Values like requires_tool, evidence_missing, or "
            "evidence_pending mean manager_action must be call_tools with estimate_nutrition; do not pair those "
            "values with manager_action=final. For composition-unknown baskets, use a composition_unknown or "
            "insufficient_details posture and final ask_followup with tool_calls=[]; do not use evidence_missing "
            "to trigger estimate_nutrition before components are known."
        )
    final_action = properties.get("final_action")
    if isinstance(final_action, dict):
        final_action["description"] = (
            "The top-level final action for this manager round. When evidence is missing, this cannot substitute "
            "for an evidence-required semantic_decision.final_action_candidate; call estimate_nutrition first. "
            "When evidence is present and semantic_decision.final_action_candidate is commit with "
            "mutation_intent_candidate canonical_write, use commit; do not use no_commit as a confirmation substitute. "
            "When workflow_effect or semantic_decision.final_action_candidate is ask_followup, set this field to "
            "ask_followup and include a concrete followup_question."
        )
    tool_calls = properties.get("tool_calls")
    if isinstance(tool_calls, dict):
        tool_calls["description"] = (
            "Required when manager_action is call_tools. Use estimate_nutrition before commit, "
            "nutrition-changing correction_applied, or overshoot_note if current-loop nutrition evidence is missing. "
            "For explicit remove_item, call resolve_correction_target when target evidence is missing; do not call it again when target evidence is already present for remove_item. "
            "Do not include estimate_nutrition for composition-unknown ask_followup/no_mutation; use final with "
            "tool_calls=[] instead."
        )
    answer_contract = properties.get("answer_contract")
    if isinstance(answer_contract, dict):
        answer_contract["description"] = (
            "Renderer-facing response contract. If semantic_decision.followup_posture is "
            "refinement_not_commit_gate or size_clarification, include a non-empty followup_question here "
            "or in semantic_decision.followup_question. If final_action is ask_followup, include the concrete "
            "question the user should answer."
        )
    semantic_decision = properties.get("semantic_decision")
    if not isinstance(semantic_decision, dict):
        return
    semantic_properties = semantic_decision.get("properties")
    if not isinstance(semantic_properties, dict):
        return
    final_action_candidate = semantic_properties.get("final_action_candidate")
    if isinstance(final_action_candidate, dict):
        final_action_candidate["description"] = (
            "The manager's intended final action after required evidence exists. If this is commit, "
            "correction_applied, or overshoot_note and evidence is missing, the current payload must be "
            "manager_action=call_tools with estimate_nutrition, not a final ask_followup/no_commit/answer_only. "
            "Explicit remove_item is a correction_applied exception when target evidence is present. If the "
            "current turn supplies concrete listed items after a basket clarification, use commit as the candidate "
            "and call estimate_nutrition instead of repeating ask_followup."
        )
    estimation_posture = semantic_properties.get("estimation_posture")
    if isinstance(estimation_posture, dict):
        estimation_posture["description"] = (
            "Estimation state for this turn. pending_tool_call or tool_pending means the same payload must use "
            "manager_action=call_tools with estimate_nutrition; do not return manager_action=final until tool "
            "results provide current-loop nutrition evidence. composition_unknown_basket is not pending_tool_call; "
            "it must pair with final ask_followup/no_mutation and tool_calls=[]."
        )
    followup_posture = semantic_properties.get("followup_posture")
    if isinstance(followup_posture, dict):
        followup_posture["description"] = (
            "Use refinement_not_commit_gate or size_clarification only with a concrete user-facing "
            "followup_question. If no question is needed, use none, closed, or refinement_optional."
        )
    followup_question = semantic_properties.get("followup_question")
    if isinstance(followup_question, dict):
        followup_question["description"] = (
            "Concrete user-facing follow-up question. Required to be non-empty when followup_posture is "
            "refinement_not_commit_gate or size_clarification, and whenever final_action is ask_followup; otherwise "
            "use null or omit by using a non-question posture."
        )


def _is_entry_scope(constraints: dict[str, Any] | None) -> bool:
    return isinstance(constraints, dict) and str(constraints.get("manager_loop_scope") or "") == "turn_entry_or_read_only"


def _is_entry_scope_route_to_intake(payload: dict[str, Any], constraints: dict[str, Any] | None) -> bool:
    return (
        _is_entry_scope(constraints)
        and str(payload.get("manager_action") or "") == "final"
        and str(payload.get("final_action") or "") == "no_commit"
        and str(payload.get("workflow_effect") or "") == "route_to_intake"
    )


def _apply_entry_scope_schema(base_schema: dict[str, Any]) -> None:
    properties = base_schema.get("properties")
    if not isinstance(properties, dict):
        return
    properties["manager_action"] = {"type": "string", "enum": ["final"]}
    properties["tool_calls"] = {
        "type": "array",
        "maxItems": 0,
        "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "arguments": {"type": "object"},
            },
            "required": ["name"],
            "additionalProperties": False,
        },
        "description": (
            "Entry scope is classification, handoff, and read-only planning only. "
            "Use tool_calls=[] and route intake execution to the intake_execution scope."
        ),
    }
    base_schema["allOf"] = [
        {
            "if": {"properties": {"manager_action": {"const": "final"}}},
            "then": {"properties": {"tool_calls": {"type": "array", "maxItems": 0}}},
        },
    ]


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
        allowed_final_actions = list(FOUNDER_LIVE_MANAGER_ALLOWED_FINAL_ACTIONS)
        base_schema["properties"]["intent_type"] = {
            "type": "string",
            "enum": list(FOUNDER_LIVE_MANAGER_ALLOWED_INTENT_TYPES),
        }
        base_schema["properties"]["final_action"] = {
            "type": "string",
            "enum": allowed_final_actions,
        }
        apply_evidence_present_final_mapping_schema(base_schema, constraints)
        base_schema["properties"]["tool_calls"] = {
            "type": "array",
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
        if _is_entry_scope(constraints):
            _apply_entry_scope_schema(base_schema)
        else:
            _apply_founder_live_contract_schema_guidance(base_schema)
            base_schema["allOf"] = [
                {
                    "if": {"properties": {"manager_action": {"const": "call_tools"}}},
                    "then": {
                        "properties": {
                            "final_action": {
                                "type": "string",
                                "enum": list(FOUNDER_LIVE_MANAGER_CALL_TOOLS_FINAL_ACTIONS),
                            },
                            "tool_calls": {"type": "array", "minItems": 1},
                        }
                    },
                },
                {
                    "if": {"properties": {"manager_action": {"const": "final"}}},
                    "then": {
                        "properties": {
                            "tool_calls": {"type": "array", "maxItems": 0},
                        }
                    },
                },
                {
                    "not": {
                        "required": ["final_action", "semantic_decision"],
                        "properties": {
                            "final_action": {"const": "no_commit"},
                            "semantic_decision": {
                                "required": ["mutation_intent_candidate"],
                                "properties": {
                                    "mutation_intent_candidate": {
                                        "enum": ["canonical_write", "correction_write"],
                                    },
                                },
                            },
                        },
                    }
                },
            ]
        if required_repair_tool:
            base_schema["properties"]["manager_action"] = {"type": "string", "enum": ["call_tools"]}
            base_schema["x-repair-contract"] = {
                "failure_family": repair_failure_family,
                "required_tool": required_repair_tool,
            }
            base_schema["required"] = list(FOUNDER_LIVE_MANAGER_REQUIRED_FIELDS)
            base_schema["x-field-consumers"] = dict(FOUNDER_LIVE_MANAGER_FIELD_CONSUMERS)
            return base_schema
        base_schema["required"] = list(FOUNDER_LIVE_MANAGER_REQUIRED_FIELDS)
        base_schema["x-field-consumers"] = dict(FOUNDER_LIVE_MANAGER_FIELD_CONSUMERS)
        return base_schema
    return manager_pass1_schema_for_constraints(base_schema, constraints)


def manager_loop_decision_transport_schema(constraints: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_founder_live_manager_contract(constraints):
        return manager_loop_schema(constraints)
    stable_constraints = dict(constraints or {})
    stable_constraints.pop("manager_loop_scope", None)
    stable_constraints.pop("available_tools", None)
    return manager_loop_schema(stable_constraints)


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
        if not _is_entry_scope_route_to_intake(payload, constraints):
            validate_founder_live_manager_contract_consistency(payload, constraints=constraints)


__all__ = [
    "ManagerPass1BranchContractError",
    "manager_loop_decision_transport_schema",
    "manager_loop_schema",
    "response_schema_for_stage",
    "validate_manager_payload",
]
