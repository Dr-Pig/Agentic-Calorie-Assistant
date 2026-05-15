from __future__ import annotations

from typing import Any

from app.shared.contracts.correction_operation import structured_correction_operation
from app.shared.contracts.correction_target import validate_correction_target_ref

PENDING_FOLLOWUP_ATTACH_REPAIR_FAMILY = "pending_followup_attach_requires_commit"
PENDING_FOLLOWUP_ATTACH_REPAIR_INSTRUCTION = (
    "A blocking pending follow-up answer for an unresolved draft completes a new meal log: "
    "use current_turn_intent='log_meal', final_action='commit', "
    "workflow_effect='commit', and mutation_intent_candidate='canonical_write'. "
    "Use correct_meal/correction_applied only for optional refinement of an already committed target."
)


def pending_followup_attach_repair_outcome(
    *,
    manager_payload: dict[str, Any],
    correction_target: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Reject a correction-shaped answer to an unresolved pending draft.

    This validates Manager-owned structured fields only. It does not inspect raw
    user text or decide whether the current turn is a pending-followup answer.
    """

    if str(manager_payload.get("final_action") or "") != "correction_applied":
        return None
    if structured_correction_operation(manager_payload) != "attach_to_pending_followup":
        return None
    target_validation = validate_correction_target_ref(correction_target)
    if target_validation.get("resolved") is True:
        return None
    return {
        "ok": False,
        "repair_request": True,
        "failure_family": PENDING_FOLLOWUP_ATTACH_REPAIR_FAMILY,
        "repair_instruction": PENDING_FOLLOWUP_ATTACH_REPAIR_INSTRUCTION,
    }


__all__ = [
    "PENDING_FOLLOWUP_ATTACH_REPAIR_FAMILY",
    "PENDING_FOLLOWUP_ATTACH_REPAIR_INSTRUCTION",
    "pending_followup_attach_repair_outcome",
]
