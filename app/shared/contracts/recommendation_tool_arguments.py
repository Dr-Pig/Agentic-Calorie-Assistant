from __future__ import annotations

from typing import Any, Mapping


TOOL_NAME = "recommendation.run"
REQUIRED_SCOPE_KEYS = ["user_id", "workspace_id", "project_id", "surface"]
ALLOWED_CALL_REF_FIELDS = [
    "memory_context_call_id",
    "query_call_id",
    "rescue_context_call_id",
    "reusable_meal_call_id",
]
FORBIDDEN_ARGUMENT_FIELDS = [
    "raw_user_input",
    "raw_transcript",
    "messages",
    "session_history",
    "prompt",
    "manager_context_packet",
]


def build_recommendation_tool_argument_contract() -> dict[str, Any]:
    return {
        "artifact_type": "shared_recommendation_tool_argument_contract",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "tool_name": TOOL_NAME,
        "required_scope_keys": list(REQUIRED_SCOPE_KEYS),
        "allowed_call_ref_fields": list(ALLOWED_CALL_REF_FIELDS),
        "forbidden_argument_fields": list(FORBIDDEN_ARGUMENT_FIELDS),
        "raw_transcript_bypass_allowed": False,
        "semantic_intent_from_raw_text_allowed": False,
        "mainline_activation_enabled": False,
        "blockers": [],
    }


def validate_recommendation_tool_arguments(arguments: Mapping[str, Any]) -> dict[str, Any]:
    scope_keys = _mapping(arguments.get("scope_keys"))
    blockers = [
        *_scope_blockers(scope_keys),
        *_forbidden_field_blockers(arguments),
        *_call_ref_blockers(arguments),
    ]
    return {
        "artifact_type": "shared_recommendation_tool_argument_validation",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "tool_name": TOOL_NAME,
        "normalized_scope_keys": {
            key: str(scope_keys.get(key) or "") for key in REQUIRED_SCOPE_KEYS
        },
        "context_call_refs": _context_call_refs(arguments),
        "raw_transcript_bypass_allowed": False,
        "semantic_intent_from_raw_text_allowed": False,
        "blockers": blockers,
    }


def _scope_blockers(scope_keys: Mapping[str, Any]) -> list[str]:
    return [
        f"scope_keys.{key}_missing"
        for key in REQUIRED_SCOPE_KEYS
        if not str(scope_keys.get(key) or "").strip()
    ]


def _forbidden_field_blockers(arguments: Mapping[str, Any]) -> list[str]:
    return [
        f"argument.{key}_forbidden"
        for key in FORBIDDEN_ARGUMENT_FIELDS
        if key in arguments
    ]


def _call_ref_blockers(arguments: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    for key, value in arguments.items():
        if key.endswith("_call_id") and key not in ALLOWED_CALL_REF_FIELDS:
            blockers.append(f"argument.{key}_unsupported_call_ref")
        if key in ALLOWED_CALL_REF_FIELDS and not str(value or "").strip():
            blockers.append(f"argument.{key}_empty")
    return blockers


def _context_call_refs(arguments: Mapping[str, Any]) -> dict[str, str]:
    return {
        key: str(arguments[key])
        for key in ALLOWED_CALL_REF_FIELDS
        if str(arguments.get(key) or "").strip()
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "ALLOWED_CALL_REF_FIELDS",
    "FORBIDDEN_ARGUMENT_FIELDS",
    "REQUIRED_SCOPE_KEYS",
    "TOOL_NAME",
    "build_recommendation_tool_argument_contract",
    "validate_recommendation_tool_arguments",
]
