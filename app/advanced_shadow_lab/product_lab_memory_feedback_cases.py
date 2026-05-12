from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.memory_feedback_projection import (
    project_feedback_event_to_shadow_controls,
)


SCOPE_KEYS = {
    "user_id": "founder-self-use",
    "workspace_id": "advanced-product-lab",
    "project_id": "agentic-calorie-assistant",
    "surface": "manager_runtime_lab",
}


def build_memory_feedback_case_reports() -> list[dict[str, Any]]:
    return [
        _case_report("memory_confirm_validator_input", "confirm"),
        _case_report("memory_reject_validator_input", "reject"),
        _case_report("memory_correct_validator_input", "correct"),
    ]


def _case_report(case_id: str, action: str) -> dict[str, Any]:
    projection = project_feedback_event_to_shadow_controls(
        feedback_event=_event(action),
        targets=[_target()],
    )
    first_projection = _first_projection(projection)
    return {
        "case_id": case_id,
        "action": action,
        "status": "pass" if _projection_passes(action, projection) else "blocked",
        "projection_status": str(projection.get("status") or ""),
        "projection_type": str(first_projection.get("projection_type") or ""),
        "validator_required": first_projection.get("validator_required") is True,
        "confirmed_memory_promoted": projection.get("confirmed_memory_promoted") is True,
        "durable_product_memory_written": projection.get(
            "durable_product_memory_written"
        )
        is True,
        "proactive_delivery_enabled": projection.get("proactive_delivery_enabled")
        is True,
        "blockers": list(projection.get("blockers") or []),
    }


def _event(action: str) -> dict[str, Any]:
    return {
        "target_type": "memory_candidate",
        "target_id": "memory-candidate-spicy",
        "action": action,
        "reason": "user_feedback",
        "source_turn_id": "turn-memory-feedback-1",
        "scope_keys": dict(SCOPE_KEYS),
    }


def _target() -> dict[str, Any]:
    return {
        "target_type": "memory_candidate",
        "target_id": "memory-candidate-spicy",
        "scope_keys": dict(SCOPE_KEYS),
        "source_turn_ids": ["turn-memory-feedback-1"],
        "source_refs": ["message:founder-profile-negative-002"],
        "candidate_type": "negative_preference",
        "trigger_type": "memory_review",
    }


def _projection_passes(action: str, projection: Mapping[str, Any]) -> bool:
    first_projection = _first_projection(projection)
    if projection.get("status") != "pass":
        return False
    if projection.get("confirmed_memory_promoted") is True:
        return False
    if projection.get("durable_product_memory_written") is True:
        return False
    if action == "confirm":
        return first_projection.get("projection_type") == (
            "memory_confirmation_validator_input"
        )
    return first_projection.get("projection_type") == "feedback_validator_input"


def _first_projection(projection: Mapping[str, Any]) -> Mapping[str, Any]:
    projections = projection.get("consumer_projections")
    if isinstance(projections, list) and projections:
        first = projections[0]
        if isinstance(first, Mapping):
            return first
    return {}


__all__ = ["SCOPE_KEYS", "build_memory_feedback_case_reports"]
