from __future__ import annotations

from typing import Any, Mapping


RECOMMENDATION_ACTIONS = {"log_this", "show_backups", "dismiss"}
RESCUE_ACTIONS = {
    "accept_rescue_plan",
    "dismiss_rescue_plan",
    "request_gentler_plan",
    "ask_why_this_plan",
}


def apply_product_lab_chat_action(
    *,
    message: Mapping[str, Any],
    action: str,
) -> dict[str, Any]:
    workflow = str(message.get("workflow_family") or "")
    if workflow == "recommendation":
        return recommendation_outcome(message=message, action=action)
    if workflow == "rescue":
        return rescue_outcome(message=message, action=action)
    return base_outcome(
        status="blocked",
        workflow_family=workflow,
        action=action,
        outcome_type="unsupported_workflow",
        blockers=[f"workflow_family_unsupported:{workflow}"],
    )


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
    outcome = base_outcome(
        status="pass",
        workflow_family="recommendation",
        action=action,
        outcome_type=recommendation_outcome_type(action),
        blockers=[],
    )
    return {
        **outcome,
        "candidate_id": str(message.get("candidate_id") or ""),
        "primary_candidate_id": str(offer.get("primary_candidate_id") or ""),
        "lab_intake_draft_created": action == "log_this",
        "backup_options_visible": action == "show_backups",
    }


def rescue_outcome(*, message: Mapping[str, Any], action: str) -> dict[str, Any]:
    if action not in RESCUE_ACTIONS:
        return base_outcome(
            status="blocked",
            workflow_family="rescue",
            action=action,
            outcome_type="unsupported_action",
            blockers=[f"rescue.action_unsupported:{action}"],
        )
    proposal = mapping(message.get("rescue_proposal"))
    outcome = base_outcome(
        status="pass",
        workflow_family="rescue",
        action=action,
        outcome_type=rescue_outcome_type(action),
        blockers=[],
    )
    return {
        **outcome,
        "candidate_id": str(message.get("candidate_id") or ""),
        "handoff_state": str(proposal.get("handoff_state") or ""),
        "lab_rescue_commit_pending": action == "accept_rescue_plan",
        "proposal_dismissed_lab": action == "dismiss_rescue_plan",
        "gentler_plan_requested": action == "request_gentler_plan",
        "proposal_committed": False,
        "ledger_entry_created": False,
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


def rescue_outcome_type(action: str) -> str:
    if action == "accept_rescue_plan":
        return "rescue_commit_confirmation"
    if action == "dismiss_rescue_plan":
        return "rescue_dismissed_lab"
    if action == "request_gentler_plan":
        return "rescue_gentler_plan_requested"
    return "rescue_explanation_requested"


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["apply_product_lab_chat_action"]
