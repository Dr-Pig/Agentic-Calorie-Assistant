from __future__ import annotations

from typing import Any

from app.composition.intake_manager_target_candidates import (
    ambiguous_default_thread_target_rejection,
    thread_target_candidates,
)
from app.shared.contracts.correction_operation import structured_correction_operation


def validate_manager_thread_target_proposal(
    *,
    correction_target: dict[str, Any],
    proposal: dict[str, Any],
) -> dict[str, Any]:
    ambiguous_default = ambiguous_default_thread_target_rejection(
        correction_target=correction_target,
        proposal=proposal,
    )
    if ambiguous_default is not None:
        return ambiguous_default
    operation = structured_correction_operation(proposal)
    proposed_thread_id = proposal.get("meal_thread_id") or proposal.get("target_object_id")
    matched_thread = _matched_thread(correction_target, proposed_thread_id)
    if matched_thread is None and proposed_thread_id is None:
        display_match = _matched_thread_by_display_name(correction_target, proposal)
        if isinstance(display_match, dict) and display_match.get("status") == "ambiguous":
            return {
                **dict(correction_target),
                "manager_target_proposal_validation": {
                    "status": "rejected",
                    "failure_family": "manager_thread_target_proposal_ambiguous",
                    "truth_owner": "deterministic_target_validator",
                    "proposal_source": str(proposal.get("target_proposal_source") or "manager_structured_output"),
                    "target_candidate_count": display_match.get("target_candidate_count"),
                    "target_candidates_supplied": True,
                    "deterministic_target_choice_allowed": False,
                },
            }
        matched_thread = display_match
    if matched_thread is not None:
        return {
            **dict(correction_target),
            "meal_thread_id": matched_thread.get("meal_thread_id"),
            "meal_version_id": matched_thread.get("meal_version_id"),
            "meal_title": matched_thread.get("meal_title") or correction_target.get("meal_title"),
            "operation": operation,
            "correction_operation": operation,
            "target_resolution_source": "manager_target_proposal_validated",
            "correction_confidence": "high",
            "manager_target_proposal_validation": {
                "status": "accepted",
                "truth_owner": "deterministic_target_validator",
                "proposal_source": str(proposal.get("target_proposal_source") or "manager_structured_output"),
            },
        }
    return {
        **dict(correction_target),
        "manager_target_proposal_validation": {
            "status": "rejected",
            "failure_family": "manager_thread_target_proposal_not_found",
            "truth_owner": "deterministic_target_validator",
        },
    }


def _matched_thread(
    correction_target: dict[str, Any],
    proposed_thread_id: Any,
) -> dict[str, Any] | None:
    if proposed_thread_id is None:
        return None
    for candidate in thread_target_candidates(correction_target):
        if str(candidate.get("meal_thread_id")) == str(proposed_thread_id):
            return candidate
    return None


def _matched_thread_by_display_name(
    correction_target: dict[str, Any],
    proposal: dict[str, Any],
) -> dict[str, Any] | None:
    display_name = str(proposal.get("target_display_name") or "").strip().casefold()
    if not display_name:
        return None
    matches = [
        candidate
        for candidate in thread_target_candidates(correction_target)
        if display_name in str(candidate.get("meal_title") or "").casefold()
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return {"status": "ambiguous", "target_candidate_count": len(matches)}
    return None
