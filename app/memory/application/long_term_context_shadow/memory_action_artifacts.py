from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.utils import (
    _list_of_dicts,
    _review_status_for_action,
    _shadow_memory_record,
)
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _memory_review_action_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    actions = _list_of_dicts(fixture.get("review_actions"))
    candidates_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    action_records: list[dict[str, Any]] = []
    candidate_results: list[dict[str, Any]] = []
    shadow_records: list[dict[str, Any]] = []
    missing_targets: list[dict[str, Any]] = []

    for action in actions:
        action_id = str(
            action.get("action_id") or f"review-action-{len(action_records) + 1}"
        )
        action_type = str(action.get("action_type") or "keep_shadowing")
        target_ids = [str(value) for value in action.get("target_candidate_ids") or []]
        action_records.append(
            {
                "action_id": action_id,
                "action_type": action_type,
                "target_candidate_ids": target_ids,
                "actor": str(action.get("actor") or "fixture_reviewer"),
                "rationale": str(action.get("rationale") or ""),
                "creates_runtime_effect": False,
                "durable_memory_write_allowed": False,
                "manager_context_injection_allowed": False,
            }
        )
        for candidate_id in target_ids:
            candidate = candidates_by_id.get(candidate_id)
            if candidate is None:
                missing_targets.append(
                    {"action_id": action_id, "candidate_id": candidate_id}
                )
                continue
            review_status_after = _review_status_for_action(action_type)
            candidate_results.append(
                {
                    "action_id": action_id,
                    "candidate_id": candidate_id,
                    "candidate_type": candidate.candidate_type,
                    "review_status_before": candidate.review_status,
                    "review_status_after": review_status_after,
                    "runtime_effect_allowed": False,
                    "durable_memory_write_allowed": False,
                    "manager_context_injection_allowed": False,
                }
            )
            if review_status_after == "accepted":
                shadow_records.append(_shadow_memory_record(candidate, action_id))

    return _base_artifact(
        artifact_type="memory_review_action_shadow_result",
        fixture=fixture,
        extra={
            "summary": {
                "action_count": len(action_records),
                "accepted_count": sum(
                    1
                    for result in candidate_results
                    if result["review_status_after"] == "accepted"
                ),
                "rejected_count": sum(
                    1
                    for result in candidate_results
                    if result["review_status_after"] == "rejected"
                ),
                "shadow_memory_record_count": len(shadow_records),
                "missing_target_count": len(missing_targets),
            },
            "action_records": action_records,
            "candidate_review_results": candidate_results,
            "shadow_memory_records": shadow_records,
            "missing_targets": missing_targets,
        },
    )


def _memory_promotion_demotion_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    action_status_by_candidate = _review_action_status_by_candidate(fixture)
    return _base_artifact(
        artifact_type="memory_promotion_demotion_shadow_eval",
        fixture=fixture,
        extra={
            "source_spec": "docs/specs/L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md",
            "promotion_attempted": False,
            "demotion_attempted": False,
            "durable_write_allowed": False,
            "promotion_review_items": [
                _promotion_review_item(candidate, action_status_by_candidate)
                for candidate in candidates
            ],
            "demotion_review_lanes": _demotion_review_lanes(),
        },
    )


def _review_action_status_by_candidate(fixture: dict[str, Any]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for action in _list_of_dicts(fixture.get("review_actions")):
        action_type = str(action.get("action_type") or "keep_shadowing")
        status = _review_status_for_action(action_type)
        for candidate_id in action.get("target_candidate_ids") or []:
            statuses[str(candidate_id)] = status
    return statuses


def _promotion_review_item(
    candidate: LongTermContextCandidate,
    action_status_by_candidate: dict[str, str],
) -> dict[str, Any]:
    review_action_status = action_status_by_candidate.get(
        candidate.candidate_id,
        candidate.review_status,
    )
    blockers = _promotion_blockers(candidate, review_action_status)
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_type": candidate.candidate_type,
        "review_action_status": review_action_status,
        "human_review_required": True,
        "promotion_allowed_now": False,
        "durable_write_allowed": False,
        "runtime_context_load_allowed": False,
        "promotion_blockers": blockers,
        "temporal_validity_required": candidate.candidate_type
        == "temporary_preference",
        "source_trace_ids": candidate.source_trace_ids,
        "source_object_refs": candidate.source_object_refs,
        "confidence": candidate.confidence,
        "freshness_posture": candidate.freshness_posture,
        "candidate_summary": candidate.proposed_memory_text,
    }


def _promotion_blockers(
    candidate: LongTermContextCandidate,
    review_action_status: str,
) -> list[str]:
    blockers: list[str] = []
    if review_action_status != "accepted":
        blockers.append("human_confirmation_required")
    if candidate.candidate_type == "temporary_preference":
        blockers.append("expiry_policy_required")
    if candidate.candidate_type == "conversation_recall_context":
        blockers.append("summary_first_retrieval_contract_required")
    if candidate.candidate_type in {
        "intake_estimation_bias",
        "logging_adherence_pattern",
        "pattern",
    }:
        blockers.append("derived_pattern_not_confirmed_memory")
    return blockers


def _demotion_review_lanes() -> list[dict[str, Any]]:
    return [
        {
            "lane_id": "expired_temporary_preference",
            "trigger": "valid_until has passed",
            "human_review_required": True,
            "automatic_runtime_effect": False,
            "durable_memory_mutation_allowed": False,
        },
        {
            "lane_id": "stale_or_contradicted_pattern",
            "trigger": "freshness posture stale or contradictory source evidence appears",
            "human_review_required": True,
            "automatic_runtime_effect": False,
            "durable_memory_mutation_allowed": False,
        },
        {
            "lane_id": "user_correction_or_deletion",
            "trigger": "user corrects, deletes, or suppresses a remembered claim",
            "human_review_required": True,
            "automatic_runtime_effect": False,
            "durable_memory_mutation_allowed": False,
        },
    ]
