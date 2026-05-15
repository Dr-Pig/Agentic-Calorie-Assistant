from __future__ import annotations

from typing import Any


def manager_item_results_schema() -> dict[str, Any]:
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


def manager_semantic_decision_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "semantic_authority": {
                "type": "string",
                "enum": ["manager_llm", "deterministic_fake_provider", "degraded_fallback", "missing"],
            },
            "current_turn_intent": {
                "type": "string",
                "enum": [
                    "log_meal",
                    "answer_query",
                    "correct_meal",
                    "complete_onboarding",
                    "answer_remaining_budget",
                    "onboarding_required",
                    "general_chat",
                    "unknown",
                ],
            },
            "target_attachment": {"type": "object"},
            "workflow_effect": {"type": "string"},
            "final_action_candidate": {"type": "string"},
            "estimation_posture": {"type": "string"},
            "followup_posture": {"type": "string"},
            "followup_question": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "followup_targets": {"type": "array", "items": {"type": "string"}},
            "mutation_intent_candidate": {
                "type": "string",
                "enum": ["canonical_write", "draft_write", "correction_write", "ledger_read", "no_mutation", "unknown"],
            },
            "uncertainty_posture": {"type": "string"},
            "base_dish": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "aliases": {"type": "array", "items": {"type": "string"}},
            "brand_hint": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "size_hint": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "modifier_hints": {"type": "array", "items": {"type": "string"}},
            "listed_items": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Manager-owned list of concrete food components from the current turn or context. "
                    "Use when the user explicitly lists concrete components; leave empty when composition is "
                    "unknown. Runtime must not fill this with a raw-text deterministic parser."
                ),
            },
            "retrieval_goal": {
                "type": "string",
                "description": (
                    "Manager-owned retrieval intent. Use listed_item_lookup for explicit listed components "
                    "that need nutrition evidence before commit; do not use generic or ask-first posture solely "
                    "because portions are rough."
                ),
            },
            "user_provided_kcal": {
                "anyOf": [{"type": "integer", "minimum": 1, "maximum": 10000}, {"type": "null"}],
                "description": (
                    "Manager-owned numeric kcal explicitly supplied by the user for this meal log. "
                    "Runtime may validate this structured field but must not extract it from raw text."
                ),
            },
            "source": {"type": "string"},
            "semantic_owner": {"type": "string"},
            "deterministic_role": {"type": "string"},
        },
        "required": [
            "semantic_authority",
            "current_turn_intent",
            "target_attachment",
            "workflow_effect",
            "final_action_candidate",
            "estimation_posture",
            "followup_posture",
            "mutation_intent_candidate",
            "uncertainty_posture",
            "source",
        ],
        "additionalProperties": False,
    }


def tool_call_names(payload: dict[str, Any]) -> list[str]:
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


def contains_any_key(value: Any, keys: set[str]) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                found.append(key)
            found.extend(contains_any_key(item, keys))
    elif isinstance(value, list):
        for item in value:
            found.extend(contains_any_key(item, keys))
    return sorted(set(found))


def actual_shape(payload: dict[str, Any]) -> str:
    manager_action = str(payload.get("manager_action") or "")
    final_action = str(payload.get("final_action") or "")
    response_mode = str(payload.get("response_mode") or "")
    workflow_effect = str(payload.get("workflow_effect") or "")
    uncertainty_posture = str(payload.get("uncertainty_posture") or "")
    names = tool_call_names(payload)
    parts: list[str] = []
    if manager_action:
        parts.append(manager_action)
    if final_action:
        parts.append(final_action)
    if names:
        parts.extend(names)
    if response_mode:
        parts.append(f"response_mode={response_mode}")
    if workflow_effect:
        parts.append(f"workflow_effect={workflow_effect}")
    if uncertainty_posture:
        parts.append(f"uncertainty_posture={uncertainty_posture}")
    if contains_any_key(payload, {"item_results", "kcal_range", "likely_kcal"}):
        parts.append("pass1_estimate_fields")
    return ".".join(parts) if parts else "empty"
