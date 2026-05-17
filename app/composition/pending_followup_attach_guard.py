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
PENDING_FOLLOWUP_EXPLICIT_TARGET_REPAIR_FAMILY = "pending_followup_commit_requires_explicit_target"
PENDING_FOLLOWUP_EXPLICIT_TARGET_REPAIR_INSTRUCTION = (
    "An open pending follow-up is present while the Manager proposed a write. "
    "You, the Manager, must explicitly choose the target posture in target_attachment: "
    "use operation='attach_to_pending_followup' with target_resolution_source='pending_followup_state' "
    "when this turn completes the pending draft, or explicitly mark a new/different target when it does not. "
    "Do not return target_attachment={} for a commit/correction while pending follow-up context is open."
)


def _manager_target_attachments(manager_payload: dict[str, Any]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for value in (manager_payload.get("target_attachment"),):
        if isinstance(value, dict) and value:
            targets.append(dict(value))
    semantic_decision = manager_payload.get("semantic_decision")
    if isinstance(semantic_decision, dict):
        semantic_target = semantic_decision.get("target_attachment")
        if isinstance(semantic_target, dict) and semantic_target:
            targets.append(dict(semantic_target))
    answer_contract = manager_payload.get("answer_contract")
    if isinstance(answer_contract, dict):
        answer_target = answer_contract.get("target_attachment")
        if isinstance(answer_target, dict) and answer_target:
            targets.append(dict(answer_target))
    return targets


def _has_explicit_target_choice(manager_payload: dict[str, Any]) -> bool:
    for target in _manager_target_attachments(manager_payload):
        for key in (
            "operation",
            "mode",
            "target_resolution_source",
            "meal_thread_id",
            "meal_id",
            "source_meal_id",
            "target_object_id",
        ):
            if str(target.get(key) or "").strip():
                return True
    return False


def _pending_followup_is_open(pending_followup: dict[str, Any] | None) -> bool:
    if not isinstance(pending_followup, dict) or not pending_followup:
        return False
    if "is_open" in pending_followup:
        return bool(pending_followup.get("is_open"))
    return True


def _pending_followup_context_present(
    *,
    correction_target: dict[str, Any] | None,
    pending_followup: dict[str, Any] | None,
) -> bool:
    if _pending_followup_is_open(pending_followup):
        return True
    if not isinstance(correction_target, dict):
        return False
    return str(correction_target.get("target_resolution_source") or "") == "pending_followup_state"


def pending_followup_attach_repair_outcome(
    *,
    manager_payload: dict[str, Any],
    correction_target: dict[str, Any] | None,
    pending_followup: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Validate Manager-owned pending-followup attach fields.

    This validates Manager-owned structured fields only. It does not inspect raw
    user text or decide whether the current turn is a pending-followup answer.
    """

    final_action = str(manager_payload.get("final_action") or "")
    if (
        _pending_followup_context_present(
            correction_target=correction_target,
            pending_followup=pending_followup,
        )
        and final_action in {"commit", "correction_applied"}
        and not _has_explicit_target_choice(manager_payload)
    ):
        return {
            "ok": False,
            "repair_request": True,
            "failure_family": PENDING_FOLLOWUP_EXPLICIT_TARGET_REPAIR_FAMILY,
            "repair_instruction": PENDING_FOLLOWUP_EXPLICIT_TARGET_REPAIR_INSTRUCTION,
        }
    if final_action != "correction_applied":
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
    "PENDING_FOLLOWUP_EXPLICIT_TARGET_REPAIR_FAMILY",
    "PENDING_FOLLOWUP_EXPLICIT_TARGET_REPAIR_INSTRUCTION",
    "pending_followup_attach_repair_outcome",
]
