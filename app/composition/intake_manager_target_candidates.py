from __future__ import annotations

from typing import Any

_DEFAULT_THREAD_TARGET_SOURCES = {
    "",
    "active_meal_view",
    "entry_manager_handoff",
    "manager_structured_output",
}
_EXPLICIT_MANAGER_TARGET_RESOLUTION_SOURCES = {
    "user_named",
    "explicit_current_turn_target",
    "manager_selected_candidate",
}


def thread_target_candidates(correction_target: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in correction_target.get("thread_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        meal_thread_id = candidate.get("meal_thread_id")
        if meal_thread_id is None:
            continue
        key = str(meal_thread_id)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(dict(candidate))
    meal_thread_id = correction_target.get("meal_thread_id")
    if meal_thread_id is not None and str(meal_thread_id) not in seen:
        candidates.append(
            {
                "meal_thread_id": meal_thread_id,
                "meal_version_id": correction_target.get("meal_version_id"),
                "meal_title": correction_target.get("meal_title"),
            }
        )
    return candidates


def ambiguous_default_thread_target_rejection(
    *,
    correction_target: dict[str, Any],
    proposal: dict[str, Any],
) -> dict[str, Any] | None:
    """Reject default thread targets when context exposes multiple legal candidates.

    This validates uniqueness only. It does not infer the intended target from text.
    """
    thread_candidates = thread_target_candidates(correction_target)
    if len(thread_candidates) < 2:
        return None
    target_resolution_source = str(proposal.get("target_resolution_source") or "").strip()
    if target_resolution_source in _EXPLICIT_MANAGER_TARGET_RESOLUTION_SOURCES:
        return None
    if str(proposal.get("target_display_name") or "").strip():
        return None
    proposed_thread_id = proposal.get("meal_thread_id") or proposal.get("target_object_id")
    default_thread_id = correction_target.get("meal_thread_id")
    if proposed_thread_id is not None and default_thread_id is not None and str(proposed_thread_id) != str(default_thread_id):
        return None
    proposal_source = str(proposal.get("target_proposal_source") or "manager_structured_output")
    if proposal_source not in _DEFAULT_THREAD_TARGET_SOURCES:
        return None
    return {
        **dict(correction_target),
        "manager_target_proposal_validation": {
            "status": "rejected",
            "failure_family": "manager_thread_target_proposal_ambiguous",
            "truth_owner": "deterministic_target_validator",
            "proposal_source": proposal_source,
            "target_candidate_count": len(thread_candidates),
            "target_candidates_supplied": True,
            "deterministic_target_choice_allowed": False,
        },
    }
