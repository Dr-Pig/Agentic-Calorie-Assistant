from __future__ import annotations

from typing import Any, Mapping


TOOL_NAME = "proactive.run"
REQUIRED_SCOPE_KEYS = ["user_id", "workspace_id", "project_id", "surface"]
REQUIRED_WAKE_SOURCE_REF_FIELDS = [
    "wake_source",
    "source_id",
    "user_relevant_reason",
    "downstream_workflow_family",
    "permission_posture",
]
ALLOWED_WAKE_SOURCES = {
    "scheduled_check",
    "state_threshold",
    "event_driven",
    "app_open",
    "manual_shadow_review",
}
ALLOWED_PERMISSION_POSTURES = {
    "user_expected",
    "user_opted_in",
    "app_open_only",
    "no_push_allowed",
    "later_requires_explicit_consent",
}
ALLOWED_CALL_REF_FIELDS = [
    "memory_context_call_id",
    "recommendation_call_id",
    "rescue_call_id",
    "pending_meal_intent_call_id",
    "control_state_call_id",
]
FORBIDDEN_ARGUMENT_FIELDS = [
    "raw_user_input",
    "raw_transcript",
    "messages",
    "session_history",
    "prompt",
    "manager_context_packet",
]


def build_proactive_tool_argument_contract() -> dict[str, Any]:
    return {
        "artifact_type": "shared_proactive_tool_argument_contract",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "tool_name": TOOL_NAME,
        "required_scope_keys": list(REQUIRED_SCOPE_KEYS),
        "required_wake_source_ref_fields": list(REQUIRED_WAKE_SOURCE_REF_FIELDS),
        "allowed_wake_sources": sorted(ALLOWED_WAKE_SOURCES),
        "allowed_permission_postures": sorted(ALLOWED_PERMISSION_POSTURES),
        "allowed_call_ref_fields": list(ALLOWED_CALL_REF_FIELDS),
        "forbidden_argument_fields": list(FORBIDDEN_ARGUMENT_FIELDS),
        "raw_transcript_bypass_allowed": False,
        "semantic_intent_from_raw_text_allowed": False,
        "production_notification_delivery_allowed": False,
        "mainline_activation_enabled": False,
        "blockers": [],
    }


def validate_proactive_tool_arguments(arguments: Mapping[str, Any]) -> dict[str, Any]:
    scope_keys = _mapping(arguments.get("scope_keys"))
    wake_ref = _mapping(arguments.get("wake_source_ref"))
    blockers = [
        *_scope_blockers(scope_keys),
        *_wake_ref_blockers(wake_ref),
        *_forbidden_field_blockers(arguments),
        *_call_ref_blockers(arguments),
    ]
    return {
        "artifact_type": "shared_proactive_tool_argument_validation",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "tool_name": TOOL_NAME,
        "normalized_scope_keys": {
            key: str(scope_keys.get(key) or "") for key in REQUIRED_SCOPE_KEYS
        },
        "wake_source_ref": {
            key: str(wake_ref.get(key) or "") for key in REQUIRED_WAKE_SOURCE_REF_FIELDS
        },
        "context_call_refs": _context_call_refs(arguments),
        "raw_transcript_bypass_allowed": False,
        "semantic_intent_from_raw_text_allowed": False,
        "production_notification_delivery_allowed": False,
        "blockers": blockers,
    }


def _scope_blockers(scope_keys: Mapping[str, Any]) -> list[str]:
    return [
        f"scope_keys.{key}_missing"
        for key in REQUIRED_SCOPE_KEYS
        if not str(scope_keys.get(key) or "").strip()
    ]


def _wake_ref_blockers(wake_ref: Mapping[str, Any]) -> list[str]:
    blockers = [
        f"wake_source_ref.{key}_missing"
        for key in REQUIRED_WAKE_SOURCE_REF_FIELDS
        if not str(wake_ref.get(key) or "").strip()
    ]
    wake_source = str(wake_ref.get("wake_source") or "")
    if wake_source and wake_source not in ALLOWED_WAKE_SOURCES:
        blockers.append(f"wake_source_ref.wake_source_unsupported:{wake_source}")
    posture = str(wake_ref.get("permission_posture") or "")
    if posture and posture not in ALLOWED_PERMISSION_POSTURES:
        blockers.append(f"wake_source_ref.permission_posture_unsupported:{posture}")
    return blockers


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
    "ALLOWED_PERMISSION_POSTURES",
    "ALLOWED_WAKE_SOURCES",
    "FORBIDDEN_ARGUMENT_FIELDS",
    "REQUIRED_SCOPE_KEYS",
    "REQUIRED_WAKE_SOURCE_REF_FIELDS",
    "TOOL_NAME",
    "build_proactive_tool_argument_contract",
    "validate_proactive_tool_arguments",
]
