from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_pending_intake_draft import (
    build_pending_intake_draft_packet,
)
from app.advanced_shadow_lab.product_lab_pending_intake_lifecycle import (
    build_pending_intake_lifecycle_packet,
)
from app.advanced_shadow_lab.product_lab_rescue_chat_action import (
    rescue_outcome,
)
from app.advanced_shadow_lab.product_lab_generic_control_action import (
    generic_control_outcome,
    is_generic_control_only,
)


RECOMMENDATION_ACTIONS = {"log_this", "show_backups", "dismiss"}


def apply_product_lab_chat_action(
    *,
    message: Mapping[str, Any],
    action: str,
) -> dict[str, Any]:
    workflow = str(message.get("workflow_family") or "")
    if is_generic_control_only(workflow=workflow, action=action):
        return generic_control_outcome(
            base_outcome=base_outcome,
            workflow_family=workflow,
            action=action,
        )
    if workflow == "recommendation":
        return recommendation_outcome(message=message, action=action)
    if workflow == "rescue":
        return rescue_outcome(
            message=message,
            action=action,
            base_outcome=base_outcome,
        )
    if workflow == "pending_intake":
        return pending_intake_outcome(message=message, action=action)
    return base_outcome(
        status="blocked",
        workflow_family=workflow,
        action=action,
        outcome_type="unsupported_workflow",
        blockers=[f"workflow_family_unsupported:{workflow}"],
    )


def apply_product_lab_chat_actions(
    *,
    messages: list[Mapping[str, Any]],
    action_specs: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_candidate_id = {
        str(message.get("candidate_id") or ""): message for message in messages
    }
    outcomes: list[dict[str, Any]] = []
    for action_spec in action_specs:
        target_candidate_id = str(action_spec.get("target_candidate_id") or "")
        action = str(action_spec.get("action") or "")
        event_id = str(action_spec.get("event_id") or "")
        message = by_candidate_id.get(target_candidate_id)
        if message is None:
            outcome = base_outcome(
                status="blocked",
                workflow_family="",
                action=action,
                outcome_type="target_candidate_not_visible",
                blockers=[f"chat_action.target_not_visible:{target_candidate_id}"],
            )
        else:
            outcome = apply_product_lab_chat_action(message=message, action=action)
        outcomes.append(
            {
                **outcome,
                "event_id": event_id,
                "target_candidate_id": target_candidate_id,
            }
        )
    return outcomes


def recommendation_outcome(
    *,
    message: Mapping[str, Any],
    action: str,
) -> dict[str, Any]:
    if action not in RECOMMENDATION_ACTIONS:
        return base_outcome(
            status="blocked",
            workflow_family="recommendation",
            action=action,
            outcome_type="unsupported_action",
            blockers=[f"recommendation.action_unsupported:{action}"],
        )
    offer = mapping(message.get("recommendation_offer"))
    pending_draft = (
        build_pending_intake_draft_packet(message=message, action=action)
        if action == "log_this"
        else {}
    )
    blockers = [
        f"pending_intake_draft.{blocker}"
        for blocker in pending_draft.get("blockers") or []
    ]
    outcome = base_outcome(
        status="blocked" if blockers else "pass",
        workflow_family="recommendation",
        action=action,
        outcome_type=recommendation_outcome_type(action),
        blockers=blockers,
    )
    return {
        **outcome,
        "candidate_id": str(message.get("candidate_id") or ""),
        "primary_candidate_id": str(offer.get("primary_candidate_id") or ""),
        "lab_intake_draft_created": pending_draft.get("status") == "pass",
        "lab_pending_intake_draft_created": pending_draft.get("status") == "pass",
        "pending_intake_draft_packet": dict(pending_draft),
        "backup_options_visible": action == "show_backups",
    }


def pending_intake_outcome(
    *,
    message: Mapping[str, Any],
    action: str,
) -> dict[str, Any]:
    packet = build_pending_intake_lifecycle_packet(message=message, action=action)
    blockers = [
        f"pending_intake_lifecycle.{blocker}"
        for blocker in packet.get("blockers") or []
    ]
    return {
        **base_outcome(
            status="blocked" if blockers else "pass",
            workflow_family="pending_intake",
            action=action,
            outcome_type=pending_intake_outcome_type(action),
            blockers=blockers,
        ),
        "candidate_id": str(message.get("candidate_id") or ""),
        "target_draft_id": str(packet.get("target_draft_id") or ""),
        "pending_intake_lifecycle_packet": dict(packet),
    }


def base_outcome(
    *,
    status: str,
    workflow_family: str,
    action: str,
    outcome_type: str,
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_chat_action_outcome",
        "status": status,
        "workflow_family": workflow_family,
        "action": action,
        "outcome_type": outcome_type,
        "served_to_mainline_user": False,
        "scheduler_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "blockers": blockers,
    }


def recommendation_outcome_type(action: str) -> str:
    if action == "log_this":
        return "recommendation_intake_draft"
    if action == "show_backups":
        return "recommendation_backups_visible"
    return "recommendation_dismissed_lab"


def pending_intake_outcome_type(action: str) -> str:
    if action == "confirm_pending_intake":
        return "pending_intake_confirmed_lab"
    if action == "cancel_pending_intake":
        return "pending_intake_canceled_lab"
    return "pending_intake_action_unsupported"


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "apply_product_lab_chat_action",
    "apply_product_lab_chat_actions",
]
