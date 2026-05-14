from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.memory_feedback_contract import NON_MUTATION_FLAGS
from app.memory.application.memory_feedback_projection import (
    project_feedback_event_to_shadow_controls,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.feedback_event_projection"
)
USER_ACTION_TO_FEEDBACK_ACTION = {
    "accept": "confirm",
    "confirm": "confirm",
    "confirm_log_this": "confirm",
    "log_this": "confirm",
    "reject": "reject",
    "dismiss": "dismiss",
    "correction": "correct",
    "correct": "correct",
    "edit_before_log": "correct",
    "reopen": "reopen",
    "modify": "modify",
    "undo": "undo",
}
LAB_FEEDBACK_ACTIONS = ["accept", "reject", "correction", "reopen"]


def build_recommendation_offer_feedback_target(
    *,
    turn_id: str,
    scope_keys: Mapping[str, Any],
    primary_candidate: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_id = str(primary_candidate.get("candidate_id") or "")
    if not candidate_id:
        return {
            "target_type": "recommendation_offer",
            "target_id": "",
            "selected_candidate_id": "",
            "scope_keys": dict(scope_keys),
            "source_turn_ids": [],
            "source_refs": [],
            "blockers": ["primary_candidate.candidate_id_missing"],
        }
    target_id = f"recommendation-offer:{turn_id}:{candidate_id}"
    return {
        "target_type": "recommendation_offer",
        "target_id": target_id,
        "selected_candidate_id": candidate_id,
        "scope_keys": dict(scope_keys),
        "source_turn_ids": [turn_id],
        "source_refs": [
            f"recommendation_offer:{target_id}",
            f"turn:{turn_id}",
            *[str(ref) for ref in primary_candidate.get("source_refs") or []],
        ],
        "blockers": [],
    }


def build_recommendation_feedback_event_projection(
    *,
    user_action: str,
    recommendation_feedback_target: Mapping[str, Any],
    reason: str = "",
) -> dict[str, Any]:
    feedback_action = USER_ACTION_TO_FEEDBACK_ACTION.get(str(user_action or ""))
    feedback_event = _feedback_event(
        target=recommendation_feedback_target,
        action=feedback_action or "",
        reason=reason,
    )
    source_projection = project_feedback_event_to_shadow_controls(
        feedback_event=feedback_event,
        targets=[recommendation_feedback_target],
    )
    blockers = [
        *([f"user_action.unsupported:{user_action}"] if feedback_action is None else []),
        *list(recommendation_feedback_target.get("blockers") or []),
        *list(source_projection.get("blockers") or []),
    ]
    return {
        "artifact_type": "recommendation_feedback_event_projection",
        "status": "pass" if not blockers else "blocked",
        "owner": "app/recommendation",
        "consumer": "manager_tool_loop_feedback_audit",
        "feedback_event_role": "audit_input_only",
        "user_action": str(user_action or ""),
        "feedback_event": feedback_event,
        "source_projection_artifact_type": source_projection.get("artifact_type"),
        "source_projection_status": source_projection.get("status"),
        "consumer_projections": list(source_projection.get("consumer_projections") or []),
        "blockers": blockers,
        "confirmed_memory_promoted": False,
        "canonical_product_mutation_allowed": False,
        "recommendation_offer_mutated": False,
        "meal_thread_mutated": False,
        "intake_committed": False,
        "ledger_entry_created": False,
        "day_budget_mutated": False,
        **dict(NON_MUTATION_FLAGS),
    }


def _feedback_event(
    *,
    target: Mapping[str, Any],
    action: str,
    reason: str,
) -> dict[str, Any]:
    source_turn_ids = [
        str(item) for item in target.get("source_turn_ids") or [] if str(item)
    ]
    return {
        "target_type": "recommendation_offer",
        "target_id": str(target.get("target_id") or ""),
        "action": action,
        "reason": reason,
        "source_turn_id": source_turn_ids[0] if source_turn_ids else "",
        "scope_keys": dict(_mapping(target.get("scope_keys"))),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "LAB_FEEDBACK_ACTIONS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_recommendation_feedback_event_projection",
    "build_recommendation_offer_feedback_target",
]
