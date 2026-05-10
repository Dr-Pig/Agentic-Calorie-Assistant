from __future__ import annotations

from typing import Any

from app.memory.domain.long_term_context_candidates import LongTermContextCandidate
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.long_term_context_shadow.lab_review_surface"
)

REVIEW_GROUPS = {
    "accepted_shadow": "active",
    "corrected_shadow": "active",
    "suppressed_shadow": "suppressed",
    "deleted_shadow": "deleted",
    "expired_shadow": "expired",
    "rejected_shadow": "rejected",
}

CHAT_ACTION_TYPES = (
    "accept_candidate",
    "confirm_candidate_semantics",
    "reject_candidate",
    "correct_candidate",
    "do_not_save_candidate",
    "suppress_candidate",
    "forget_memory_record",
    "delete_candidate",
    "expire_candidate",
)
USER_EQUIVALENT_ACTION_TYPES = {
    "confirm_candidate_semantics",
    "do_not_save_candidate",
    "forget_memory_record",
}


def lab_review_correction_surface(
    *,
    candidates: list[LongTermContextCandidate],
    records: list[dict[str, Any]],
    blockers: list[str],
) -> dict[str, Any]:
    groups = _empty_groups()
    pending_cards: list[dict[str, Any]] = []
    commands: list[dict[str, Any]] = []
    if not blockers:
        groups = _review_state_groups(records)
        pending_cards = _pending_candidate_cards(candidates, records)
        commands = _chat_commands()
    return {
        "surface_type": "chat_first_memory_review_correction_surface",
        "source_artifact_type": "memory_lab_review_loop_state",
        "status": "blocked" if blockers else "generated",
        "primary_surface": "chat",
        "runtime_route_mounted": False,
        "api_route_mounted": False,
        "product_settings_surface_added": False,
        "runtime_effect_allowed": False,
        "durable_memory_written": False,
        "manager_context_injection_allowed": False,
        "truth_owner": "human_reviewer",
        "deterministic_role": "present_state_validate_command_preconditions_only",
        "llm_role": "none",
        "deterministic_semantic_inference_allowed": False,
        "blockers": blockers,
        "summary": _summary(groups, pending_cards, blockers),
        "review_state_groups": groups,
        "pending_candidate_cards": pending_cards,
        "available_chat_commands": commands,
        "blocked_runtime_commands": _blocked_runtime_commands(),
    }


def _empty_groups() -> dict[str, list[dict[str, Any]]]:
    return {
        "active": [],
        "suppressed": [],
        "deleted": [],
        "expired": [],
        "rejected": [],
    }


def _review_state_groups(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups = _empty_groups()
    for record in records:
        group = REVIEW_GROUPS[str(record["record_state"])]
        groups[group].append(_reviewed_record_card(record))
    return groups


def _reviewed_record_card(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "memory_record_id": record["memory_record_id"],
        "source_candidate_id": record["source_candidate_id"],
        "record_state": record["record_state"],
        "revision": record["revision"],
        "memory_text": record["memory_text"],
        "candidate_type": record["candidate_type"],
        "active_in_lab_context": record["active_in_lab_context"],
        "excluded_from_lab_context_reason": record[
            "excluded_from_lab_context_reason"
        ],
        "audit_provenance_retained": record["audit_provenance_retained"],
        "runtime_effect_allowed": False,
        "durable_memory_written": False,
        "manager_context_injection_allowed": False,
    }


def _pending_candidate_cards(
    candidates: list[LongTermContextCandidate],
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reviewed_ids = {str(record["source_candidate_id"]) for record in records}
    return [
        {
            "candidate_id": candidate.candidate_id,
            "candidate_type": candidate.candidate_type,
            "proposed_memory_text": candidate.proposed_memory_text,
            "review_status": candidate.review_status,
            "intended_consumers": candidate.intended_consumers,
            "source_trace_ids": candidate.source_trace_ids,
            "runtime_effect_allowed": False,
            "durable_memory_write_allowed": False,
            "manager_context_injection_allowed": False,
        }
        for candidate in candidates
        if candidate.candidate_id not in reviewed_ids
    ]


def _chat_commands() -> list[dict[str, Any]]:
    return [
        {
            "command_id": f"chat_memory_review.{action_type}",
            "action_type": action_type,
            "source": "fixture_review_actions_only",
            "requires_human_reviewer": True,
            "creates_runtime_effect": False,
            "durable_memory_write_allowed": False,
            "manager_context_injection_allowed": False,
            "fixture_only_user_equivalent_semantics": (
                action_type in USER_EQUIVALENT_ACTION_TYPES
            ),
            "user_facing_behavior_changed_in_mainline": False,
        }
        for action_type in CHAT_ACTION_TYPES
    ]


def _blocked_runtime_commands() -> list[dict[str, Any]]:
    return [
        _blocked_command(
            "promote_to_runtime_memory",
            "requires durable memory activation plan and human promotion gate",
        ),
        _blocked_command(
            "inject_manager_context",
            "requires ManagerContextPacket activation gate",
        ),
        _blocked_command(
            "mount_memory_settings_route",
            "user-visible memory settings surface is forbidden in this phase",
        ),
    ]


def _blocked_command(command_id: str, reason: str) -> dict[str, Any]:
    return {
        "command_id": command_id,
        "blocked": True,
        "reason": reason,
        "runtime_effect_allowed": False,
        "durable_memory_write_allowed": False,
        "manager_context_injection_allowed": False,
    }


def _summary(
    groups: dict[str, list[dict[str, Any]]],
    pending_cards: list[dict[str, Any]],
    blockers: list[str],
) -> dict[str, int]:
    return {
        "active_record_count": len(groups["active"]),
        "suppressed_record_count": len(groups["suppressed"]),
        "deleted_record_count": len(groups["deleted"]),
        "expired_record_count": len(groups["expired"]),
        "rejected_record_count": len(groups["rejected"]),
        "pending_candidate_count": len(pending_cards),
        "blocker_count": len(blockers),
    }


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "lab_review_correction_surface"]
