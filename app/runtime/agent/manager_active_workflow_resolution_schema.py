from __future__ import annotations

from typing import Any

CURRENT_TURN_RELATIONS = [
    "answers_required_slot",
    "answers_optional_slot",
    "basis_inquiry",
    "correction",
    "removal",
    "unrelated_new_log",
    "ambiguous",
    "none",
]

SLOT_KINDS = [
    "composition_items",
    "portion_amount",
    "drink_size",
    "sugar_level",
    "topping",
    "cooking_method",
    "missing_component_confirmation",
    "target_selection",
    "other",
]


def manager_slot_update_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "slot_id": {
                "type": "string",
                "description": "Manager-owned slot id from active_workflow.required_slots or optional_slots.",
            },
            "slot_kind": {
                "type": "string",
                "enum": SLOT_KINDS,
                "description": "The slot family being resolved. Do not invent route-specific slot kinds.",
            },
            "required_for_commit": {
                "type": "boolean",
                "description": "Mirror the active workflow slot posture; Manager decides whether the turn answers it.",
            },
            "current_value": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "number"},
                    {"type": "boolean"},
                    {"type": "null"},
                ],
                "description": "Structured value extracted by the Manager from the current turn or known context.",
            },
            "source": {
                "type": "string",
                "description": (
                    "Where the Manager found the value, such as current_turn, active_workflow_context, "
                    "tool_result, or unresolved."
                ),
            },
            "resolution_condition": {
                "type": "string",
                "description": "Human-readable condition that makes the slot resolved or still missing.",
            },
            "asked_question": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "Prior assistant question this slot answers, when applicable.",
            },
        },
        "required": [
            "slot_id",
            "slot_kind",
            "required_for_commit",
            "current_value",
            "source",
            "resolution_condition",
            "asked_question",
        ],
        "additionalProperties": False,
    }


def manager_missing_slot_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "slot_id": {"type": "string"},
            "slot_kind": {"type": "string", "enum": SLOT_KINDS},
            "required_for_commit": {"type": "boolean"},
            "missing_reason": {"type": "string"},
        },
        "required": ["slot_id", "slot_kind", "required_for_commit", "missing_reason"],
        "additionalProperties": False,
    }


def manager_active_workflow_resolution_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "description": (
            "Manager-owned resolution of how the current turn relates to active workflow context. "
            "Context supplies candidates only; runtime must not fill this from raw text."
        ),
        "properties": {
            "current_turn_relation": {
                "type": "string",
                "enum": CURRENT_TURN_RELATIONS,
                "description": (
                    "Manager decision for the current turn relation to pending, active meal, target "
                    "candidates, or no active workflow."
                ),
            },
            "slot_updates": {
                "type": "array",
                "items": manager_slot_update_schema(),
                "description": "Slots the Manager decided were answered or updated by this turn.",
            },
            "still_missing_slots": {
                "type": "array",
                "items": manager_missing_slot_schema(),
                "description": "Slots that remain unresolved after the Manager considered the current turn.",
            },
            "attach_target": {
                "type": "object",
                "description": (
                    "Manager-selected attach/correction/removal target or empty object. "
                    "Must be selected from model-visible candidates when a target is needed."
                ),
            },
            "final_action": {
                "type": "string",
                "description": "Manager's intended final action for this active workflow resolution.",
            },
            "resolution_basis": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Compact basis refs, such as current_turn, pending_followup, or target_candidates.",
            },
            "selection_owner": {
                "type": "string",
                "enum": ["manager"],
                "description": "Manager owns active workflow resolution.",
            },
            "deterministic_role": {
                "type": "string",
                "enum": ["validate_only"],
                "description": "Deterministic code validates this resolution but does not create it.",
            },
        },
        "required": [
            "current_turn_relation",
            "slot_updates",
            "still_missing_slots",
            "attach_target",
            "final_action",
            "resolution_basis",
            "selection_owner",
            "deterministic_role",
        ],
        "additionalProperties": False,
    }
