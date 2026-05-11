from __future__ import annotations

from typing import Any, Callable, Mapping

from app.advanced_shadow_lab.product_lab_calibration_action_decision import (
    build_calibration_action_decision_packet,
)


CALIBRATION_ACTIONS = {
    "accept_calibration_proposal",
    "dismiss_calibration_proposal",
    "view_calibration_alternatives",
}


def calibration_outcome(
    *,
    message: Mapping[str, Any],
    action: str,
    base_outcome: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    if action not in CALIBRATION_ACTIONS:
        return base_outcome(
            status="blocked",
            workflow_family="calibration",
            action=action,
            outcome_type="unsupported_action",
            blockers=[f"calibration.action_unsupported:{action}"],
        )
    decision = build_calibration_action_decision_packet(message=message, action=action)
    blockers = [
        f"calibration_action_decision.{blocker}"
        for blocker in decision.get("blockers") or []
    ]
    return {
        **base_outcome(
            status="blocked" if blockers else "pass",
            workflow_family="calibration",
            action=action,
            outcome_type=calibration_outcome_type(action),
            blockers=blockers,
        ),
        "candidate_id": str(message.get("candidate_id") or ""),
        "lab_calibration_effect_applied": (
            decision.get("lab_calibration_effect_applied") is True
        ),
        "calibration_proposal_dismissed_lab": (
            decision.get("proposal_instance_dismissed") is True
        ),
        "calibration_action_decision_packet": decision,
        "proposal_committed": False,
        "body_plan_mutated": False,
    }


def calibration_outcome_type(action: str) -> str:
    if action == "accept_calibration_proposal":
        return "calibration_effect_applied_lab"
    if action == "dismiss_calibration_proposal":
        return "calibration_proposal_dismissed_lab"
    return "calibration_alternatives_visible_lab"


__all__ = ["calibration_outcome"]
