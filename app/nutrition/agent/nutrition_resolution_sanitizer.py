from __future__ import annotations

from typing import Any

from .nutrition_resolution_prompt import (
    VALID_ACTION_TAKEN,
    VALID_CONFIDENCE_TIERS,
    VALID_ESTIMATE_MODES,
    VALID_EXACTNESS,
    VALID_RESOLUTION_BASES,
    VALID_RESOLUTION_MODES,
    VALID_RESPONSE_MODE_HINTS,
)


def sanitize_literal(value: Any, valid_set: set[str], default: str) -> str:
    if value is None:
        return default
    normalized = str(value).strip().lower()
    return normalized if normalized in valid_set else default


def sanitize_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def sanitize_list(value: Any, max_length: int = 50) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        return [value] if value else []
    return value[:max_length]


def normalize_confidence(value: Any) -> str:
    if value is None:
        return "low"
    normalized = str(value).strip().lower()
    if normalized in VALID_CONFIDENCE_TIERS:
        return normalized
    if "medium" in normalized:
        return "medium"
    if "high" in normalized and "low" not in normalized:
        return "high"
    if "low" in normalized and "high" not in normalized:
        return "low"
    return "medium"


def validate_structured_answer(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}

    sanitized: dict[str, Any] = {}
    literal_fields = {
        "action_taken": (VALID_ACTION_TAKEN, "clarify_before_estimate"),
        "confidence": (VALID_CONFIDENCE_TIERS, "low"),
        "exactness": (VALID_EXACTNESS, "unknown"),
        "resolution_mode": (VALID_RESOLUTION_MODES, "cannot_estimate_yet"),
        "resolution_basis": (VALID_RESOLUTION_BASES, "component_model"),
        "response_mode_hint": (VALID_RESPONSE_MODE_HINTS, "clarify_first"),
        "estimate_mode": (VALID_ESTIMATE_MODES, "llm_only"),
    }
    int_fields = {"protein_g", "carb_g", "fat_g", "estimated_kcal", "kcal_low", "kcal_high", "kcal_most_likely"}
    list_fields = {
        "components",
        "items",
        "uncertainty_factors",
        "blockers",
        "missing_slots",
        "blocking_slots",
        "unresolved_info",
        "top_uncertainty_drivers",
        "heuristic_dependencies",
    }
    bool_fields = {"follow_up_needed", "clarification_blocking"}
    string_fields = {
        "title",
        "tool_request",
        "state_transition_hint",
        "followup_question",
        "follow_up_reasoning",
        "tool_request_reason",
        "why_no_more_tools",
        "current_evidence_sufficiency",
        "reason_for_not_requesting_tool",
        "portion_reason",
        "why_not_exact",
    }

    for key, value in raw.items():
        if key in literal_fields:
            valid_set, default = literal_fields[key]
            sanitized[key] = normalize_confidence(value) if key == "confidence" else sanitize_literal(value, valid_set, default)
        elif key in int_fields:
            sanitized[key] = sanitize_int(value)
        elif key in list_fields:
            sanitized[key] = sanitize_list(value)
        elif key in bool_fields:
            sanitized[key] = bool(value)
        elif key in string_fields:
            sanitized[key] = str(value or "").strip()[:500]
        elif key == "portion_multiplier":
            try:
                sanitized[key] = float(value if value is not None else 1.0)
            except (TypeError, ValueError):
                sanitized[key] = 1.0
        elif key == "answer_payload":
            sanitized[key] = dict(value or {})
        else:
            sanitized[key] = value

    sanitized["_raw_validated"] = True
    return sanitized
