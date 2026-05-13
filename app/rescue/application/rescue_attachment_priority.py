from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.rescue_attachment_priority"
)
RESCUE_PROPOSAL = "rescue_proposal"
INTAKE_FOLLOWUP = "intake_followup"
ACTION_CONTRACTS = {
    "explicit_accept": ("accept_rescue_plan", "accept_rescue_plan_lab_contract"),
    "explicit_dismiss": ("dismiss_rescue_plan", "dismiss_rescue_plan_lab_contract"),
}
NEGOTIATION_SEMANTICS = {"explicit_adjust", "explain_request"}
ANSWER_ONLY_SEMANTICS = {
    "complaint_or_hardness_feedback",
    "feasibility_question",
    "hesitation",
    "ambiguous",
}
NO_ATTACH_SEMANTICS = {"topic_reset"}
FALSE_OUTPUT_FLAGS = {
    "runtime_effect_allowed": False,
    "canonical_mutation_changed": False,
    "mainline_activation_enabled": False,
    "production_db_mutation_allowed": False,
    "production_scheduler_delivery_allowed": False,
    "durable_product_memory_written_in_mainline": False,
    "manager_context_packet_changed_in_mainline": False,
}


def build_rescue_attachment_priority_contract(
    *,
    manager_attachment_packet: Mapping[str, Any],
) -> dict[str, Any]:
    manager_semantics = _mapping(manager_attachment_packet.get("manager_semantics"))
    blockers = _packet_blockers(manager_attachment_packet, manager_semantics)
    if blockers:
        return _artifact(status="blocked", blockers=blockers)
    return _artifact(
        status="pass",
        attachment_decision=_attachment_decision(
            manager_semantics=manager_semantics,
            open_objects=_open_objects(manager_attachment_packet),
        ),
    )


def _artifact(
    *,
    status: str,
    blockers: list[str] | None = None,
    attachment_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "rescue_attachment_priority_contract",
        "status": status,
        "owner": "app/rescue",
        "consumer": "manager_rescue_action_router",
        "attachment_decision": attachment_decision,
        "raw_utterance_used_for_semantic_classification": False,
        "deterministic_role": "validate_and_project_manager_semantics",
        "llm_role": "classify_user_intent_and_action_semantics",
        "blockers": blockers or [],
        **dict(FALSE_OUTPUT_FLAGS),
    }


def _packet_blockers(
    packet: Mapping[str, Any],
    manager_semantics: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if packet.get("artifact_type") != "manager_rescue_attachment_packet":
        blockers.append("manager_attachment_packet.unsupported_artifact_type")
    if packet.get("status") != "pass":
        blockers.append("manager_attachment_packet.status_not_pass")
    if not manager_semantics:
        blockers.append("manager_attachment_packet.manager_semantics_missing")
        return blockers
    semantic = str(manager_semantics.get("semantic") or "")
    if not semantic:
        blockers.append("manager_semantics.semantic_missing")
    if semantic in ACTION_CONTRACTS or semantic in NEGOTIATION_SEMANTICS:
        rescue_id = _object_id(_open_objects(packet), RESCUE_PROPOSAL)
        if not rescue_id:
            blockers.append("open_objects.rescue_proposal_missing")
    if semantic == "followup_answer":
        followup_id = _object_id(_open_objects(packet), INTAKE_FOLLOWUP)
        if not followup_id:
            blockers.append("open_objects.intake_followup_missing")
    return blockers


def _attachment_decision(
    *,
    manager_semantics: Mapping[str, Any],
    open_objects: list[Mapping[str, Any]],
) -> dict[str, Any]:
    semantic = str(manager_semantics.get("semantic") or "")
    if semantic in ACTION_CONTRACTS:
        return _rescue_action_decision(
            semantic=semantic,
            rescue_proposal_id=_object_id(open_objects, RESCUE_PROPOSAL),
        )
    if semantic in NEGOTIATION_SEMANTICS:
        return _rescue_negotiation_decision(
            semantic=semantic,
            rescue_proposal_id=_object_id(open_objects, RESCUE_PROPOSAL),
        )
    if semantic == "followup_answer":
        return {
            "disposition": "attach_intake_followup",
            "target_object_type": INTAKE_FOLLOWUP,
            "target_object_id": _object_id(open_objects, INTAKE_FOLLOWUP),
            "mutation_allowed_in_lab": False,
            "next_contract": "intake_followup_answer_contract",
            "rescue_proposal_state_mutation_allowed": False,
            "reason": "explicit_followup_answer_has_priority_over_open_rescue",
        }
    if semantic in ANSWER_ONLY_SEMANTICS:
        return _answer_only_decision(semantic)
    if semantic in NO_ATTACH_SEMANTICS:
        return _no_attach_decision(semantic)
    return _answer_only_decision("unknown_or_unsupported_semantic")


def _rescue_action_decision(*, semantic: str, rescue_proposal_id: str) -> dict[str, Any]:
    action_id, next_contract = ACTION_CONTRACTS[semantic]
    return {
        "disposition": "attach_rescue_proposal_action",
        "target_object_type": RESCUE_PROPOSAL,
        "target_object_id": rescue_proposal_id,
        "target_action": action_id,
        "mutation_allowed_in_lab": True,
        "next_contract": next_contract,
        "rescue_proposal_state_mutation_allowed": True,
        "reason": "explicit_rescue_action_semantics",
    }


def _rescue_negotiation_decision(
    *,
    semantic: str,
    rescue_proposal_id: str,
) -> dict[str, Any]:
    return {
        "disposition": "attach_rescue_proposal_negotiation",
        "target_object_type": RESCUE_PROPOSAL,
        "target_object_id": rescue_proposal_id,
        "target_action": "negotiate_rescue_plan",
        "mutation_allowed_in_lab": False,
        "next_contract": "rescue_negotiation_response_contract",
        "rescue_proposal_state_mutation_allowed": False,
        "reason": semantic,
    }


def _answer_only_decision(semantic: str) -> dict[str, Any]:
    return {
        "disposition": "answer_only",
        "target_object_type": None,
        "target_object_id": None,
        "target_action": "answer_without_state_change",
        "mutation_allowed_in_lab": False,
        "next_contract": "rescue_answer_only_response_contract",
        "rescue_proposal_state_mutation_allowed": False,
        "reason": semantic,
    }


def _no_attach_decision(semantic: str) -> dict[str, Any]:
    return {
        "disposition": "start_new_workflow_or_defer",
        "target_object_type": None,
        "target_object_id": None,
        "target_action": "no_attach",
        "mutation_allowed_in_lab": False,
        "next_contract": "manager_topic_reset_contract",
        "rescue_proposal_state_mutation_allowed": False,
        "reason": semantic,
    }


def _open_objects(packet: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [item for item in packet.get("open_objects", []) if isinstance(item, Mapping)]


def _object_id(open_objects: list[Mapping[str, Any]], object_type: str) -> str:
    for item in open_objects:
        if item.get("object_type") == object_type and item.get("status") == "open":
            return str(item.get("object_id") or "")
    return ""


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_attachment_priority_contract",
]
