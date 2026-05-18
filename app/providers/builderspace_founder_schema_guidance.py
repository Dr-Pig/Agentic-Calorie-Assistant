from __future__ import annotations

from typing import Any

from .builderspace_target_attachment_schema import apply_target_attachment_schema_guidance
from ..runtime.agent.founder_live_manager_allowed_values import (
    founder_live_manager_call_tools_final_actions_for_constraints,
)


def apply_founder_live_contract_schema_guidance(base_schema: dict[str, Any]) -> None:
    properties = base_schema.get("properties")
    if not isinstance(properties, dict):
        return
    if isinstance(manager_action := properties.get("manager_action"), dict):
        manager_action["description"] = (
            "Use call_tools when current-loop evidence is still required. If "
            "semantic_decision.final_action_candidate is commit, correction_applied, or overshoot_note "
            "and manager_contract_evidence_state.nutrition_evidence_present is false, this field must be "
            "call_tools with estimate_nutrition; do not return final with ask_followup, answer_only, or no_commit "
            "as a substitute. If evidence_posture says requires_tool/evidence_missing/evidence_pending or "
            "semantic_decision.estimation_posture says pending_tool_call/tool_pending, this field must be call_tools. "
            "Exception: explicit remove_item correction uses target evidence from resolve_correction_target, not estimate_nutrition. "
            "If target_evidence_present is true with target_evidence_operation remove_item, return final correction_applied and do not call resolve_correction_target again. Exception: composition-unknown baskets or unanchored patterned combos are not tool evidence missing; return final "
            "ask_followup with tool_calls=[] instead of call_tools; manager_action=call_tools is invalid for composition-unknown "
            "baskets or unanchored patterned combos. Every call_tools response must include a non-empty "
            "tool_calls array."
        )
    if isinstance(evidence_posture := properties.get("evidence_posture"), dict):
        evidence_posture["description"] = (
            "Evidence status for this manager round. Values like requires_tool, evidence_missing, or "
            "evidence_pending mean manager_action must be call_tools with estimate_nutrition; do not pair those "
            "values with manager_action=final. For composition-unknown baskets or unanchored patterned combos, use a composition_unknown or "
            "insufficient_details posture and final ask_followup with tool_calls=[]; do not use evidence_missing "
            "to trigger estimate_nutrition before components are known."
        )
    _apply_top_level_final_mapping_guidance(properties)
    semantic_decision = properties.get("semantic_decision")
    if not isinstance(semantic_decision, dict):
        return
    semantic_properties = semantic_decision.get("properties")
    if not isinstance(semantic_properties, dict):
        return
    _apply_semantic_decision_guidance(semantic_properties)
    apply_target_attachment_schema_guidance(properties, semantic_properties)


def apply_entry_scope_schema(base_schema: dict[str, Any]) -> None:
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


def founder_live_manager_all_of_rules(constraints: dict[str, Any] | None) -> list[dict[str, Any]]:
    body_handoff_rules: list[dict[str, Any]] = []
    if not is_body_observation_scope(constraints):
        body_handoff_rules.append(_body_observation_handoff_rule())
    return [
        {
            "if": {"properties": {"manager_action": {"const": "call_tools"}}},
            "then": {
                "properties": {
                    "final_action": {
                        "type": "string",
                        "enum": founder_live_manager_call_tools_final_actions_for_constraints(constraints),
                    },
                    "tool_calls": {"type": "array", "minItems": 1},
                }
            },
        },
        {
            "if": {"properties": {"manager_action": {"const": "final"}}},
            "then": {"properties": {"tool_calls": {"type": "array", "maxItems": 0}}},
        },
        *body_handoff_rules,
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


def is_entry_scope(constraints: dict[str, Any] | None) -> bool:
    return isinstance(constraints, dict) and str(constraints.get("manager_loop_scope") or "") == "turn_entry_or_read_only"


def is_entry_scope_route_to_intake(payload: dict[str, Any], constraints: dict[str, Any] | None) -> bool:
    return (
        is_entry_scope(constraints)
        and str(payload.get("manager_action") or "") == "final"
        and str(payload.get("final_action") or "") == "no_commit"
        and str(payload.get("workflow_effect") or "") == "route_to_intake"
    )


def requires_scope_specific_decision_transport_schema(constraints: dict[str, Any]) -> bool:
    if str(constraints.get("manager_loop_scope") or "") == "body_observation":
        return True
    return bool(constraints.get("guard_feedback_repair_request")) and (
        str(constraints.get("guard_feedback_failure_family") or "")
        == "body_observation_missing_successful_tool_result"
    )


def is_body_observation_scope(constraints: dict[str, Any] | None) -> bool:
    return isinstance(constraints, dict) and str(constraints.get("manager_loop_scope") or "") == "body_observation"


def _apply_top_level_final_mapping_guidance(properties: dict[str, Any]) -> None:
    if isinstance(workflow_effect := properties.get("workflow_effect"), dict):
        workflow_effect["description"] = (
            "Evidence-present intake final mapping: runtime workflow effect for the current manager scope. "
            "route_to_intake is only an entry-scope handoff. After current-loop nutrition evidence is present "
            "for an estimable intake write or correction, intake_execution final mapping must not remain route_to_intake; use commit, correction, or overshoot "
            "according to semantic_decision.final_action_candidate."
        )
    if isinstance(final_action := properties.get("final_action"), dict):
        final_action["description"] = (
            "The top-level final action for this manager round. When evidence is missing, this cannot substitute "
            "for an evidence-required semantic_decision.final_action_candidate; call estimate_nutrition first. "
            "When evidence is present and semantic_decision.final_action_candidate is commit with "
            "mutation_intent_candidate canonical_write, use commit; do not use no_commit as a confirmation substitute. "
            "When workflow_effect or semantic_decision.final_action_candidate is ask_followup, set this field to "
            "ask_followup and include a concrete followup_question."
        )
    if isinstance(tool_calls := properties.get("tool_calls"), dict):
        tool_calls["description"] = (
            "Required when manager_action is call_tools. Use estimate_nutrition before commit, "
            "nutrition-changing correction_applied, or overshoot_note if current-loop nutrition evidence is missing. "
            "For explicit remove_item, call resolve_correction_target when target evidence is missing; do not call it again when target evidence is already present for remove_item. "
            "Do not include estimate_nutrition for composition-unknown ask_followup/no_mutation; use final with "
            "tool_calls=[] instead."
        )
        _apply_tool_call_argument_shape_guidance(tool_calls)
    if isinstance(answer_contract := properties.get("answer_contract"), dict):
        answer_contract["description"] = (
            "Renderer-facing response contract. If semantic_decision.followup_posture is "
            "refinement_not_commit_gate or size_clarification, include a non-empty followup_question here "
            "or in semantic_decision.followup_question. If final_action is ask_followup, include the concrete "
            "question the user should answer."
        )


def _apply_semantic_decision_guidance(semantic_properties: dict[str, Any]) -> None:
    if isinstance(final_action_candidate := semantic_properties.get("final_action_candidate"), dict):
        final_action_candidate["description"] = (
            "The manager's intended final action after required evidence exists. If this is commit, "
            "correction_applied, or overshoot_note and evidence is missing, the current payload must be "
            "manager_action=call_tools with estimate_nutrition, not a final ask_followup/no_commit/answer_only. "
            "Explicit remove_item is a correction_applied exception when target evidence is present. If the "
            "current turn supplies concrete listed items after a basket clarification, use commit as the candidate "
            "and call estimate_nutrition instead of repeating ask_followup."
        )
    if isinstance(estimation_posture := semantic_properties.get("estimation_posture"), dict):
        estimation_posture["description"] = (
            "Estimation state for this turn. pending_tool_call or tool_pending means the same payload must use "
            "manager_action=call_tools with estimate_nutrition; do not return manager_action=final until tool "
            "results provide current-loop nutrition evidence. composition_unknown_basket or unanchored_patterned_combo is not pending_tool_call; "
            "the LLM semantic decision must pair it with final ask_followup/no_mutation and tool_calls=[]."
        )
    if isinstance(followup_posture := semantic_properties.get("followup_posture"), dict):
        followup_posture["description"] = (
            "Use refinement_not_commit_gate or size_clarification only with a concrete user-facing "
            "followup_question. If no question is needed, use none, closed, or refinement_optional."
        )
    if isinstance(followup_question := semantic_properties.get("followup_question"), dict):
        followup_question["description"] = (
            "Concrete user-facing follow-up question. Required to be non-empty when followup_posture is "
            "refinement_not_commit_gate or size_clarification, and whenever final_action is ask_followup; otherwise "
            "use null or omit by using a non-question posture."
        )


def _apply_tool_call_argument_shape_guidance(tool_calls: dict[str, Any]) -> None:
    items = tool_calls.get("items")
    if not isinstance(items, dict):
        return
    items.setdefault("allOf", []).append(
        {
            "if": {
                "required": ["name"],
                "properties": {"name": {"const": "resolve_correction_target"}},
            },
            "then": {
                "properties": {
                    "arguments": {
                        "type": "object",
                        "properties": {
                            "meal_thread_id": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
                            "meal_item_id": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
                            "canonical_name": {"type": "string"},
                            "target_display_name": {"type": "string"},
                            "meal_version_id": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
                            "operation": {"type": "string"},
                            "target_proposal_source": {"type": "string"},
                        },
                        "anyOf": [
                            {"required": ["meal_thread_id"]},
                            {"required": ["meal_item_id"]},
                            {"required": ["canonical_name"]},
                            {"required": ["target_display_name"]},
                        ],
                        "additionalProperties": False,
                    }
                }
            },
        }
    )
    items.setdefault("allOf", []).append(
        {
            "if": {
                "required": ["name"],
                "properties": {"name": {"const": "estimate_nutrition"}},
            },
            "then": {
                "properties": {
                    "arguments": {
                        "type": "object",
                        "properties": {
                            "manager_semantic_decision": {
                                "type": "object",
                                "description": (
                                    "Manager-owned evidence target for estimate_nutrition. "
                                    "Do not rely on raw user text. Provide base_dish, aliases, "
                                    "brand_hint plus size_hint, or multiple listed_items."
                                ),
                                "properties": {
                                    "base_dish": {"type": "string"},
                                    "aliases": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "minItems": 1,
                                    },
                                    "brand_hint": {"type": "string"},
                                    "size_hint": {"type": "string"},
                                    "listed_items": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "minItems": 2,
                                    },
                                    "retrieval_goal": {"type": "string"},
                                    "semantic_authority_source": {"type": "string"},
                                },
                                "anyOf": [
                                    {"required": ["base_dish"]},
                                    {"required": ["aliases"]},
                                    {"required": ["brand_hint", "size_hint"]},
                                    {"required": ["listed_items"]},
                                ],
                                "additionalProperties": True,
                            },
                            "handoff_source": {"type": "string"},
                            "deterministic_role": {"type": "string"},
                        },
                        "required": ["manager_semantic_decision"],
                        "additionalProperties": True,
                    }
                }
            },
        }
    )


def _body_observation_handoff_rule() -> dict[str, Any]:
    return {
        "if": {"properties": {"intent_type": {"const": "body_observation"}}},
        "then": {
            "properties": {
                "manager_action": {"type": "string", "enum": ["final"]},
                "final_action": {"type": "string", "enum": ["no_commit"]},
                "workflow_effect": {"type": "string", "enum": ["route_to_body_observation"]},
                "tool_calls": {"type": "array", "maxItems": 0},
            }
        },
    }
