from __future__ import annotations

from typing import Any, Callable, Mapping

from app.advanced_shadow_lab.product_lab_rescue_action_decision import (
    build_rescue_action_decision_packet,
)


RESCUE_ACTIONS = {
    "accept_rescue_plan",
    "dismiss_rescue_plan",
    "request_gentler_plan",
    "ask_why_this_plan",
}


def rescue_outcome(
    *,
    message: Mapping[str, Any],
    action: str,
    base_outcome: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    if action not in RESCUE_ACTIONS:
        return base_outcome(
            status="blocked",
            workflow_family="rescue",
            action=action,
            outcome_type="unsupported_action",
            blockers=[f"rescue.action_unsupported:{action}"],
        )
    proposal = _mapping(message.get("rescue_proposal"))
    decision = build_rescue_action_decision_packet(message=message, action=action)
    blockers = [
        f"rescue_action_decision.{blocker}"
        for blocker in decision.get("blockers") or []
    ]
    outcome = base_outcome(
        status="blocked" if blockers else "pass",
        workflow_family="rescue",
        action=action,
        outcome_type=rescue_outcome_type(action),
        blockers=blockers,
    )
    return {
        **outcome,
        "candidate_id": str(message.get("candidate_id") or ""),
        "handoff_state": str(proposal.get("handoff_state") or ""),
        "lab_rescue_commit_pending": (
            decision.get("lab_rescue_commit_pending") is True
        ),
        "proposal_dismissed_lab": (
            decision.get("proposal_instance_dismissed") is True
        ),
        "gentler_plan_requested": decision.get("decision_kind")
        == "request_gentler_variant",
        "rescue_action_decision_packet": decision,
        "proposal_committed": False,
        "ledger_entry_created": False,
    }


def rescue_outcome_type(action: str) -> str:
    if action == "accept_rescue_plan":
        return "rescue_commit_confirmation"
    if action == "dismiss_rescue_plan":
        return "rescue_dismissed_lab"
    if action == "request_gentler_plan":
        return "rescue_gentler_plan_requested"
    return "rescue_explanation_requested"


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["rescue_outcome"]
