from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.memory_feedback_contract"
)

REQUIRED_SCOPE_KEYS = ("user_id", "workspace_id", "project_id", "surface")
MEMORY_RECORD_TYPES = {
    "confirmed_preference",
    "pattern_memory",
    "temporary_preference",
    "negative_preference",
    "suppression_rule",
    "golden_order",
    "recall_summary",
}
MEMORY_FAMILIES = {
    "diet_product",
    "app_interaction",
    "proactive_control",
    "conversation_recall",
}
MEMORY_STATUSES = {
    "candidate",
    "pending_review",
    "confirmed",
    "rejected",
    "archived",
    "superseded",
}
POLARITIES = {"positive", "negative", "neutral"}
STRENGTHS = {"boost", "downrank", "block"}

FEEDBACK_TARGET_TYPES = {
    "memory_candidate",
    "proactive_candidate",
    "recommendation_offer",
    "rescue_plan",
}
FEEDBACK_ACTIONS = {
    "confirm",
    "reject",
    "dismiss",
    "snooze",
    "reopen",
    "modify",
    "undo",
    "correct",
    "opt_out",
}
TARGET_ACTIONS = {
    "memory_candidate": {"confirm", "reject", "correct", "undo"},
    "proactive_candidate": {"dismiss", "snooze", "reopen", "modify", "undo", "opt_out"},
    "recommendation_offer": {"confirm", "reject", "dismiss", "snooze", "reopen", "modify", "undo", "correct"},
    "rescue_plan": {"confirm", "reject", "dismiss", "snooze", "reopen", "modify", "undo", "correct"},
}
NON_MUTATION_FLAGS = {
    "mutates_truth_directly": False,
    "runtime_connected": False,
    "lab_isolated": True,
    "runtime_effect_allowed": False,
    "durable_product_memory_written": False,
    "canonical_mutation_changed": False,
    "manager_context_packet_changed": False,
    "scheduler_delivery_allowed": False,
    "user_facing_behavior_changed": False,
}

def validate_memory_record_contract(record: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _normalize_memory_record(record)
    blockers = _memory_record_blockers(normalized)
    return {
        "artifact_type": "memory_record_contract_validation",
        "status": "pass" if not blockers else "blocked",
        "normalized_record": normalized if not blockers else {},
        "blockers": blockers,
        **NON_MUTATION_FLAGS,
    }

def validate_feedback_event_contract(event: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _normalize_feedback_event(event)
    blockers = _feedback_event_blockers(normalized)
    target_type = normalized.get("target_type")
    action = normalized.get("action")
    may_satisfy_memory_gate = (
        not blockers and target_type == "memory_candidate" and action == "confirm"
    )
    return {
        "artifact_type": "feedback_event_contract_validation",
        "status": "pass" if not blockers else "blocked",
        "normalized_event": normalized if not blockers else {},
        "blockers": blockers,
        "may_satisfy_memory_confirmation_gate": may_satisfy_memory_gate,
        **NON_MUTATION_FLAGS,
    }


def _normalize_memory_record(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(record.get("id") or ""),
        "record_type": str(record.get("record_type") or ""),
        "family": str(record.get("family") or ""),
        "status": str(record.get("status") or ""),
        "summary": str(record.get("summary") or "").strip(),
        "polarity": str(record.get("polarity") or ""),
        "strength": str(record.get("strength") or ""),
        "scope_keys": _scope_keys(record.get("scope_keys")),
        "source_refs": _string_list(record.get("source_refs")),
        "consumers": _string_list(record.get("consumers")),
        "validity": record.get("validity"),
        "history": _string_list(record.get("history")),
    }


def _normalize_feedback_event(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "target_type": str(event.get("target_type") or ""),
        "target_id": str(event.get("target_id") or ""),
        "action": str(event.get("action") or ""),
        "reason": str(event.get("reason") or ""),
        "snooze_until": event.get("snooze_until"),
        "source_turn_id": str(event.get("source_turn_id") or ""),
        "scope_keys": _scope_keys(event.get("scope_keys")),
    }


def _memory_record_blockers(record: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    _require_value(blockers, record, "id")
    _require_enum(blockers, record, "record_type", MEMORY_RECORD_TYPES)
    _require_enum(blockers, record, "family", MEMORY_FAMILIES)
    _require_enum(blockers, record, "status", MEMORY_STATUSES)
    _require_value(blockers, record, "summary")
    _require_enum(blockers, record, "polarity", POLARITIES)
    _require_enum(blockers, record, "strength", STRENGTHS)
    blockers.extend(_scope_blockers(record.get("scope_keys")))
    if not record.get("source_refs"):
        blockers.append("source_refs.missing")
    if not record.get("consumers"):
        blockers.append("consumers.missing")
    return blockers


def _feedback_event_blockers(event: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    _require_enum(blockers, event, "target_type", FEEDBACK_TARGET_TYPES)
    _require_value(blockers, event, "target_id")
    _require_enum(blockers, event, "action", FEEDBACK_ACTIONS)
    _require_value(blockers, event, "source_turn_id")
    blockers.extend(_scope_blockers(event.get("scope_keys")))
    target_type = str(event.get("target_type") or "")
    action = str(event.get("action") or "")
    if target_type in TARGET_ACTIONS and action and action not in TARGET_ACTIONS[target_type]:
        blockers.append(f"action.illegal_for_target:{target_type}.{action}")
    if action == "snooze" and not event.get("snooze_until"):
        blockers.append("snooze_until.missing")
    return blockers


def _require_value(blockers: list[str], payload: Mapping[str, Any], field: str) -> None:
    if not payload.get(field):
        blockers.append(f"{field}.missing")


def _require_enum(
    blockers: list[str], payload: Mapping[str, Any], field: str, allowed: set[str]
) -> None:
    value = str(payload.get(field) or "")
    if value not in allowed:
        blockers.append(f"{field}.unsupported:{value}")


def _scope_blockers(value: object) -> list[str]:
    scope = _scope_keys(value)
    missing = [key for key in REQUIRED_SCOPE_KEYS if not scope.get(key)]
    return [f"scope_keys.missing:{','.join(missing)}"] if missing else []


def _scope_keys(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {key: str(value[key]) for key in value if value.get(key)}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


__all__ = [
    "FEEDBACK_ACTIONS", "FEEDBACK_TARGET_TYPES", "MEMORY_FAMILIES",
    "MEMORY_RECORD_TYPES", "MEMORY_STATUSES", "POLARITIES",
    "REQUIRED_SCOPE_KEYS", "SIDECAR_ACTIVATION_CONTRACT", "STRENGTHS",
    "TARGET_ACTIONS", "validate_feedback_event_contract",
    "validate_memory_record_contract",
]
