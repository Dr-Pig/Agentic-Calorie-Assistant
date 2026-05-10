from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.lab_review_surface import (
    lab_review_correction_surface,
)
from app.memory.application.long_term_context_shadow.memory_review_controls import (
    excluded_reason,
    is_user_equivalent_action,
    record_review_flags,
    review_control_semantics,
)
from app.memory.application.long_term_context_shadow.utils import _list_of_dicts
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.long_term_context_shadow.lab_store"
)

STATE_BY_ACTION_TYPE = {
    "accept_candidate": "accepted_shadow",
    "confirm_candidate_semantics": "accepted_shadow",
    "reject_candidate": "rejected_shadow",
    "correct_candidate": "corrected_shadow",
    "do_not_save_candidate": "suppressed_shadow",
    "suppress_candidate": "suppressed_shadow",
    "forget_memory_record": "deleted_shadow",
    "delete_candidate": "deleted_shadow",
    "expire_candidate": "expired_shadow",
}

SUPPORTED_ACTION_TYPES = set(STATE_BY_ACTION_TYPE)

EXCLUSION_REASON_BY_STATE = {
    "rejected_shadow": "rejected_by_reviewer",
    "suppressed_shadow": "suppressed_by_reviewer",
    "deleted_shadow": "deleted_by_reviewer",
    "expired_shadow": "expired_by_reviewer",
}

ACTIVE_STATES = {"accepted_shadow", "corrected_shadow"}


def _memory_lab_review_loop_state_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    actions = _list_of_dicts(fixture.get("review_actions"))
    candidates_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    blockers = _action_blockers(actions, candidates_by_id)
    records = [] if blockers else _reduce_actions(actions, candidates_by_id)
    summary = _summary(actions, records, blockers)
    return _base_artifact(
        artifact_type="memory_lab_review_loop_state",
        fixture=fixture,
        extra={
            "status": "blocked" if blockers else "generated",
            "lab_isolated": True,
            "mainline_runtime_connected": False,
            "user_facing_behavior_changed_in_mainline": False,
            "canonical_mutation_changed_in_mainline": False,
            "durable_product_memory_written_in_mainline": False,
            "manager_context_packet_changed_in_mainline": False,
            "real_scheduler_or_notification_delivery": False,
            "lab_artifacts_may_include_complete_ux": True,
            "lab_state_reducer": "deterministic_human_review_action_reducer",
            "truth_owner": "human_reviewer",
            "deterministic_role": "validate_scope_apply_audit_and_exclusion",
            "llm_role": "none",
            "review_control_semantics": review_control_semantics(),
            "summary": summary,
            "blockers": blockers,
            "lab_memory_records": records,
            "lab_review_correction_surface": lab_review_correction_surface(
                candidates=candidates,
                records=records,
                blockers=blockers,
            ),
            "active_context_candidate_ids": [
                record["source_candidate_id"]
                for record in records
                if record["active_in_lab_context"]
            ],
            "excluded_context_candidate_ids": [
                record["source_candidate_id"]
                for record in records
                if not record["active_in_lab_context"]
            ],
        },
    )


def _action_blockers(
    actions: list[dict[str, Any]],
    candidates_by_id: dict[str, LongTermContextCandidate],
) -> list[str]:
    blockers: list[str] = []
    for action in actions:
        action_id = str(action.get("action_id") or "review-action")
        action_type = str(action.get("action_type") or "")
        target_ids = [str(value) for value in action.get("target_candidate_ids") or []]
        if action_type not in SUPPORTED_ACTION_TYPES:
            blockers.append(f"{action_id}.unsupported_action_type:{action_type}")
        if not action.get("actor"):
            blockers.append(f"{action_id}.missing_actor")
        if not target_ids:
            blockers.append(f"{action_id}.missing_target_candidate_ids")
        if action_type == "correct_candidate" and not action.get(
            "corrected_memory_text"
        ):
            blockers.append(f"{action_id}.missing_corrected_memory_text")
        for flag in (
            "creates_runtime_effect",
            "durable_memory_write_allowed",
            "manager_context_injection_allowed",
        ):
            if action.get(flag) is True:
                blockers.append(f"{action_id}.{flag}")
        for candidate_id in target_ids:
            if candidate_id not in candidates_by_id:
                blockers.append(f"{action_id}.unknown_target_candidate:{candidate_id}")
    return blockers


def _reduce_actions(
    actions: list[dict[str, Any]],
    candidates_by_id: dict[str, LongTermContextCandidate],
) -> list[dict[str, Any]]:
    records_by_id: dict[str, dict[str, Any]] = {}
    record_order: list[str] = []
    for action in actions:
        for candidate_id in action.get("target_candidate_ids") or []:
            candidate = candidates_by_id[str(candidate_id)]
            existing = records_by_id.get(candidate.candidate_id)
            records_by_id[candidate.candidate_id] = _apply_action(
                existing,
                candidate,
                action,
            )
            if candidate.candidate_id not in record_order:
                record_order.append(candidate.candidate_id)
    return [records_by_id[candidate_id] for candidate_id in record_order]


def _apply_action(
    existing: dict[str, Any] | None,
    candidate: LongTermContextCandidate,
    action: dict[str, Any],
) -> dict[str, Any]:
    action_type = str(action["action_type"])
    record_state = STATE_BY_ACTION_TYPE[action_type]
    revision = int(existing.get("revision", 0)) + 1 if existing else 1
    memory_text = None
    if record_state != "deleted_shadow":
        memory_text = (
            str(action["corrected_memory_text"])
            if record_state == "corrected_shadow"
            else candidate.proposed_memory_text
        )
    audit_log = [*(existing or {}).get("audit_log", [])]
    audit_log.append(
        {
            "action_id": str(action.get("action_id") or "review-action"),
            "action_type": action_type,
            "actor": str(action.get("actor") or ""),
            "rationale": str(action.get("rationale") or ""),
            "source_candidate_id": candidate.candidate_id,
            "record_state_before": (existing or {}).get("record_state", "none"),
            "record_state_after": record_state,
            "revision_after": revision,
            "runtime_effect_allowed": False,
            "durable_memory_written": False,
            "manager_context_injected": False,
            "user_equivalent_memory_control": is_user_equivalent_action(action_type),
        }
    )
    active = record_state in ACTIVE_STATES
    return {
        "memory_record_id": f"lab-shadow-memory-record-{candidate.candidate_id}",
        "source_candidate_id": candidate.candidate_id,
        "source_action_id": str(action.get("action_id") or "review-action"),
        "record_state": record_state,
        "revision": revision,
        "memory_text": memory_text,
        "candidate_type": candidate.candidate_type,
        "scope_keys": candidate.scope_keys,
        "intended_consumers": candidate.intended_consumers,
        "active_in_lab_context": active,
        "excluded_from_lab_context_reason": (
            None
            if active
            else excluded_reason(record_state, action_type, EXCLUSION_REASON_BY_STATE)
        ),
        **record_review_flags(action_type),
        "can_be_runtime_loaded": False,
        "durable_memory_written": False,
        "runtime_effect_allowed": False,
        "manager_context_injected": False,
        "canonical_mutation_changed": False,
        "audit_provenance_retained": True,
        "provenance": {
            "source_trace_ids": candidate.source_trace_ids,
            "source_object_refs": candidate.source_object_refs,
            "evidence_count": candidate.evidence_count,
        },
        "audit_log": audit_log,
    }


def _summary(
    actions: list[dict[str, Any]],
    records: list[dict[str, Any]],
    blockers: list[str],
) -> dict[str, int]:
    states = [record["record_state"] for record in records]
    return {
        "action_count": len(actions),
        "applied_action_count": (
            sum(len(action.get("target_candidate_ids") or []) for action in actions)
            if not blockers
            else 0
        ),
        "active_record_count": sum(
            1 for record in records if record["active_in_lab_context"]
        ),
        "suppressed_record_count": states.count("suppressed_shadow"),
        "deleted_record_count": states.count("deleted_shadow"),
        "expired_record_count": states.count("expired_shadow"),
        "blocker_count": len(blockers),
    }


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "_memory_lab_review_loop_state_artifact"]
