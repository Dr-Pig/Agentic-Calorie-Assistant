from __future__ import annotations

from typing import Any

_TRANSPORT_WORKFLOW_EFFECTS = [
    "answer_only",
    "ask_followup",
    "canonical_write",
    "commit",
    "correction",
    "correction_applied",
    "correction_write",
    "estimate_with_followup",
    "manual_daily_target_update",
    "onboarding_required",
    "overshoot_note",
    "pending_evidence",
    "route_to_intake",
    "safe_failure",
    "seed_active_body_plan_and_day_budget",
    "target_updated",
]


def compact_decision_transport_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove prompt-only schema prose from provider transport copies."""

    compacted = _compact(schema)
    _apply_transport_enums(compacted)
    return compacted


def _apply_transport_enums(schema: dict[str, Any]) -> None:
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return
    workflow_effect = properties.get("workflow_effect")
    if isinstance(workflow_effect, dict) and "enum" not in workflow_effect:
        workflow_effect["enum"] = list(_TRANSPORT_WORKFLOW_EFFECTS)


def _compact(value: Any) -> Any:
    if isinstance(value, dict):
        compacted: dict[str, Any] = {}
        for key, item in value.items():
            if key == "description" or key.startswith("x-"):
                continue
            compacted[key] = _compact(item)
        return compacted
    if isinstance(value, list):
        return [_compact(item) for item in value]
    return value


__all__ = ["compact_decision_transport_schema"]
