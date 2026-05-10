from __future__ import annotations

from typing import Any, Callable


GENERIC_CONTROL_ACTIONS = {"dismiss", "snooze", "undo"}


def is_generic_control_only(*, workflow: str, action: str) -> bool:
    if action not in GENERIC_CONTROL_ACTIONS:
        return False
    if workflow == "recommendation" and action == "dismiss":
        return False
    return True


def generic_control_outcome(
    *,
    base_outcome: Callable[..., dict[str, Any]],
    workflow_family: str,
    action: str,
) -> dict[str, Any]:
    return {
        **base_outcome(
            status="pass",
            workflow_family=workflow_family,
            action=action,
            outcome_type="candidate_control_requested_lab",
            blockers=[],
        ),
        "control_action_requested": True,
    }


__all__ = ["generic_control_outcome", "is_generic_control_only"]
