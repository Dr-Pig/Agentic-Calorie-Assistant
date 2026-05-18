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


def validate_active_workflow_resolution_shape(
    semantic_decision: dict[str, Any],
    *,
    expected_final_action: str | None = None,
) -> None:
    resolution = semantic_decision.get("active_workflow_resolution")
    if not isinstance(resolution, dict):
        raise RuntimeError(
            "manager semantic_decision.active_workflow_resolution missing or not object; "
            "Manager must explicitly resolve active workflow relation"
        )
    _require_keys(
        resolution,
        [
            "current_turn_relation",
            "slot_updates",
            "still_missing_slots",
            "attach_target",
            "final_action",
            "resolution_basis",
            "selection_owner",
            "deterministic_role",
        ],
        path="semantic_decision.active_workflow_resolution",
    )
    relation = str(resolution.get("current_turn_relation") or "")
    if relation not in CURRENT_TURN_RELATIONS:
        raise RuntimeError(f"semantic_decision.active_workflow_resolution.current_turn_relation invalid: {relation!r}")
    if resolution.get("selection_owner") != "manager":
        raise RuntimeError("semantic_decision.active_workflow_resolution.selection_owner must be 'manager'")
    if resolution.get("deterministic_role") != "validate_only":
        raise RuntimeError("semantic_decision.active_workflow_resolution.deterministic_role must be 'validate_only'")
    if not isinstance(resolution.get("attach_target"), dict):
        raise RuntimeError("semantic_decision.active_workflow_resolution.attach_target must be an object")
    if not isinstance(resolution.get("resolution_basis"), list):
        raise RuntimeError("semantic_decision.active_workflow_resolution.resolution_basis must be a list")
    active_relation_requires_final_action_alignment = relation not in {
        "none",
        "unrelated_new_log",
        "ambiguous",
    }
    expected = str(expected_final_action or semantic_decision.get("final_action_candidate") or "").strip()
    actual = str(resolution.get("final_action") or "").strip()
    if active_relation_requires_final_action_alignment and expected and actual != expected:
        raise RuntimeError(
            "semantic_decision.active_workflow_resolution.final_action must match "
            "semantic_decision.final_action_candidate"
        )
    _validate_slot_updates(resolution.get("slot_updates"))
    _validate_missing_slots(resolution.get("still_missing_slots"))


def _require_keys(value: dict[str, Any], keys: list[str], *, path: str) -> None:
    missing = [key for key in keys if key not in value]
    if missing:
        raise RuntimeError(f"{path} missing required fields: {missing}")


def _validate_slot_updates(value: Any) -> None:
    if not isinstance(value, list):
        raise RuntimeError("semantic_decision.active_workflow_resolution.slot_updates must be a list")
    for index, item in enumerate(value):
        path = f"semantic_decision.active_workflow_resolution.slot_updates[{index}]"
        if not isinstance(item, dict):
            raise RuntimeError(f"{path} must be an object")
        _require_keys(
            item,
            [
                "slot_id",
                "slot_kind",
                "required_for_commit",
                "current_value",
                "source",
                "resolution_condition",
                "asked_question",
            ],
            path=path,
        )
        _validate_slot_kind(item.get("slot_kind"), path=path)
        if not isinstance(item.get("required_for_commit"), bool):
            raise RuntimeError(f"{path}.required_for_commit must be boolean")


def _validate_missing_slots(value: Any) -> None:
    if not isinstance(value, list):
        raise RuntimeError("semantic_decision.active_workflow_resolution.still_missing_slots must be a list")
    for index, item in enumerate(value):
        path = f"semantic_decision.active_workflow_resolution.still_missing_slots[{index}]"
        if not isinstance(item, dict):
            raise RuntimeError(f"{path} must be an object")
        _require_keys(item, ["slot_id", "slot_kind", "required_for_commit", "missing_reason"], path=path)
        _validate_slot_kind(item.get("slot_kind"), path=path)
        if not isinstance(item.get("required_for_commit"), bool):
            raise RuntimeError(f"{path}.required_for_commit must be boolean")


def _validate_slot_kind(value: Any, *, path: str) -> None:
    slot_kind = str(value or "")
    if slot_kind not in SLOT_KINDS:
        raise RuntimeError(f"{path}.slot_kind invalid: {slot_kind!r}")
