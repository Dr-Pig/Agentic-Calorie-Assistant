from __future__ import annotations

from typing import Any

from app.shared.contracts.correction_operation import structured_correction_operation

FOUNDER_LIVE_MANAGER_TARGET_AMBIGUITY_REPAIR_FAMILY = "manager_thread_target_proposal_ambiguous"


def target_evidence_state(tool_results: list[dict[str, Any]] | None) -> dict[str, Any]:
    for item in tool_results or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("tool_name") or item.get("name") or "").strip()
        if name != "resolve_correction_target" or item.get("failure_family"):
            continue
        provenance = item.get("provenance")
        evidence = item.get("evidence")
        target = {}
        if isinstance(provenance, dict) and isinstance(provenance.get("correction_target"), dict):
            target = dict(provenance["correction_target"])
        elif isinstance(evidence, dict) and isinstance(evidence.get("correction_target"), dict):
            target = dict(evidence["correction_target"])
        operation = structured_correction_operation(target)
        validation = target.get("manager_target_proposal_validation")
        if isinstance(validation, dict) and validation.get("status") == "rejected":
            continue
        if target.get("meal_thread_id") is not None and (
            target.get("meal_item_id") is not None or operation == "remove_meal"
        ):
            return {
                "target_evidence_present": True,
                "target_evidence_source": "resolve_correction_target",
                "target_evidence_operation": operation or None,
            }
    return {
        "target_evidence_present": False,
        "target_evidence_source": None,
        "target_evidence_operation": None,
    }


def target_validation_rejection_state(tool_results: list[dict[str, Any]] | None) -> dict[str, Any]:
    for item in tool_results or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("tool_name") or item.get("name") or "").strip()
        if name != "resolve_correction_target":
            continue
        provenance = item.get("provenance")
        target = {}
        if isinstance(provenance, dict) and isinstance(provenance.get("correction_target"), dict):
            target = dict(provenance["correction_target"])
        validation = target.get("manager_target_proposal_validation")
        if isinstance(validation, dict) and validation.get("status") == "rejected":
            return {
                "present": True,
                "failure_family": str(validation.get("failure_family") or ""),
            }
    return {"present": False, "failure_family": None}


def target_evidence_present(evidence_state: Any) -> bool:
    return isinstance(evidence_state, dict) and evidence_state.get("target_evidence_present") is True


def target_ambiguity_repair_required(evidence_state: Any) -> bool:
    if not isinstance(evidence_state, dict):
        return False
    return evidence_state.get("target_validation_failure_family") == FOUNDER_LIVE_MANAGER_TARGET_AMBIGUITY_REPAIR_FAMILY


def validate_target_ambiguity_repair(
    *,
    payload: dict[str, Any],
    semantic_decision: dict[str, Any],
    final_action: str,
) -> None:
    workflow_effect = str(payload.get("workflow_effect") or semantic_decision.get("workflow_effect") or "")
    final_action_candidate = str(semantic_decision.get("final_action_candidate") or "")
    mutation_intent = str(semantic_decision.get("mutation_intent_candidate") or "")
    followup_question = ""
    answer_contract = payload.get("answer_contract")
    if isinstance(answer_contract, dict):
        followup_question = str(answer_contract.get("followup_question") or "").strip()
    followup_question = followup_question or str(semantic_decision.get("followup_question") or "").strip()
    if (
        str(payload.get("manager_action") or "") == "final"
        and final_action == "ask_followup"
        and workflow_effect == "ask_followup"
        and final_action_candidate == "ask_followup"
        and mutation_intent == "no_mutation"
        and followup_question
    ):
        return
    raise RuntimeError(
        "founder live manager contract ambiguous correction target requires final ask_followup "
        "target clarification with no mutation after target validation rejected multiple candidates"
    )


__all__ = [
    "FOUNDER_LIVE_MANAGER_TARGET_AMBIGUITY_REPAIR_FAMILY",
    "target_ambiguity_repair_required",
    "target_evidence_present",
    "target_evidence_state",
    "target_validation_rejection_state",
    "validate_target_ambiguity_repair",
]
