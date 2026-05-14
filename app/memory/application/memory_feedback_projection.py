from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.memory_feedback_contract import (
    NON_MUTATION_FLAGS,
    validate_feedback_event_contract,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.memory_feedback_projection"
)


def project_feedback_event_to_shadow_controls(
    *,
    feedback_event: Mapping[str, Any],
    targets: list[Mapping[str, Any]],
) -> dict[str, Any]:
    validation = validate_feedback_event_contract(feedback_event)
    target = _find_target(feedback_event, targets)
    blockers = [
        *validation["blockers"],
        *_target_blockers(feedback_event, target),
    ]
    projections = [] if blockers else _projections(feedback_event, target or {})
    return {
        "artifact_type": "memory_feedback_event_projection",
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "normalized_event": validation.get("normalized_event", {}),
        "consumer_projections": projections,
        "user_control_event_projected": any(
            projection["projection_type"].startswith("user_control")
            for projection in projections
        ),
        "confirmed_memory_promoted": False,
        "proactive_delivery_enabled": False,
        "confirm_enables_proactive_delivery": False,
        "recommendation_offer_mutated": False,
        "rescue_plan_mutated": False,
        **NON_MUTATION_FLAGS,
    }


def _find_target(
    event: Mapping[str, Any], targets: list[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    target_type = str(event.get("target_type") or "")
    target_id = str(event.get("target_id") or "")
    for target in targets:
        if (
            str(target.get("target_type") or "") == target_type
            and str(target.get("target_id") or "") == target_id
        ):
            return target
    return None


def _target_blockers(
    event: Mapping[str, Any], target: Mapping[str, Any] | None
) -> list[str]:
    target_type = str(event.get("target_type") or "")
    target_id = str(event.get("target_id") or "")
    if target is None:
        return [f"target.not_found:{target_type}.{target_id}"]

    blockers: list[str] = []
    if not _scope_matches(event, target):
        blockers.append("target.scope_mismatch")
    source_turn_id = str(event.get("source_turn_id") or "")
    source_turn_ids = [str(item) for item in target.get("source_turn_ids", []) if item]
    if source_turn_id not in source_turn_ids:
        blockers.append(f"target.source_turn_mismatch:{source_turn_id}")
    if not target.get("source_refs"):
        blockers.append("target.source_refs.missing")
    return blockers


def _scope_matches(event: Mapping[str, Any], target: Mapping[str, Any]) -> bool:
    event_scope = _mapping(event.get("scope_keys"))
    target_scope = _mapping(target.get("scope_keys"))
    for key, value in event_scope.items():
        if str(target_scope.get(key) or "") != str(value):
            return False
    return bool(event_scope)


def _projections(
    event: Mapping[str, Any], target: Mapping[str, Any]
) -> list[dict[str, Any]]:
    action = str(event.get("action") or "")
    target_type = str(event.get("target_type") or "")
    if target_type == "memory_candidate" and action == "confirm":
        return [_memory_confirmation_projection(event, target)]
    if action == "dismiss":
        return [_dismiss_projection(event, target)]
    if action == "snooze":
        return [_snooze_projection(event, target)]
    if action == "undo":
        return [_undo_projection(event, target, projection_type="user_control_undo")]
    if action in {"reopen", "modify"}:
        return [
            _undo_projection(
                event,
                target,
                projection_type="user_control_reopen_modify",
            )
        ]
    if action == "opt_out":
        return [
            _opt_out_projection(event, target, "proactive_suppression_candidate"),
            _opt_out_projection(event, target, "app_use_memory_candidate"),
        ]
    return [_feedback_projection(event, target)]


def _memory_confirmation_projection(
    event: Mapping[str, Any], target: Mapping[str, Any]
) -> dict[str, Any]:
    return _base_projection(event, target) | {
        "projection_type": "memory_confirmation_validator_input",
        "candidate_type": str(target.get("candidate_type") or ""),
        "may_satisfy_memory_confirmation_gate": True,
        "validator_required": True,
        "confirmed_memory_promoted": False,
        "auto_promotes_memory": False,
    }


def _dismiss_projection(event: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    return _base_projection(event, target) | {
        "projection_type": "user_control_suppression",
        "dismiss_reason": str(event.get("reason") or ""),
        "next_signal_required": str(target.get("next_signal_required") or ""),
        "auto_promotes_memory": False,
    }


def _snooze_projection(event: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    return _base_projection(event, target) | {
        "projection_type": "user_control_snooze",
        "snooze_until": str(event.get("snooze_until") or ""),
        "auto_promotes_memory": False,
    }


def _undo_projection(
    event: Mapping[str, Any],
    target: Mapping[str, Any],
    *,
    projection_type: str,
) -> dict[str, Any]:
    return _base_projection(event, target) | {
        "projection_type": projection_type,
        "auto_promotes_memory": False,
    }


def _opt_out_projection(
    event: Mapping[str, Any], target: Mapping[str, Any], projection_type: str
) -> dict[str, Any]:
    return _base_projection(event, target) | {
        "projection_type": projection_type,
        "opt_out_reason": str(event.get("reason") or ""),
        "validator_required": True,
        "auto_promotes_memory": False,
    }


def _feedback_projection(event: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    return _base_projection(event, target) | {
        "projection_type": "feedback_validator_input",
        "validator_required": True,
        "auto_promotes_memory": False,
    }


def _base_projection(
    event: Mapping[str, Any], target: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "target_type": str(event.get("target_type") or ""),
        "target_id": str(event.get("target_id") or ""),
        "action": str(event.get("action") or ""),
        "source_turn_id": str(event.get("source_turn_id") or ""),
        "source_refs": [str(ref) for ref in target.get("source_refs", []) if ref],
        "trigger_type": str(target.get("trigger_type") or ""),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "project_feedback_event_to_shadow_controls",
]
