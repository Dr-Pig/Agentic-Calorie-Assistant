from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "runtime.application.proactive_no_send_control_path_evidence"
)

CONTROL_ACTIONS = ("dismiss", "snooze", "undo")


def build_no_send_control_path_evidence(
    *,
    no_send_candidates: list[Mapping[str, Any]],
    interaction_artifacts: list[Mapping[str, Any]],
) -> dict[str, Any]:
    configured_paths = {
        "dismiss": _all_candidates_have_dismiss(no_send_candidates),
        "snooze": _all_candidates_have_snooze(no_send_candidates),
        "undo": _all_candidates_have_undo(no_send_candidates),
    }
    next_signal_present = _all_candidates_have_next_signal(no_send_candidates)
    complete = bool(no_send_candidates) and all(configured_paths.values()) and next_signal_present
    observed = _observed_actions(interaction_artifacts)
    return {
        "status": "pass" if complete else _empty_or_blocked(no_send_candidates),
        "candidate_count": len(no_send_candidates),
        "all_candidates_have_required_controls": complete,
        "configured_paths": configured_paths,
        "interaction_actions_observed": observed,
        "observed_all_interaction_actions": all(action in observed for action in CONTROL_ACTIONS),
        "next_signal_required_present": next_signal_present,
    }


def _all_candidates_have_dismiss(candidates: list[Mapping[str, Any]]) -> bool:
    return bool(candidates) and all(
        isinstance(candidate.get("dismiss_reason_choices"), list)
        and bool(candidate.get("dismiss_reason_choices"))
        for candidate in candidates
    )


def _all_candidates_have_snooze(candidates: list[Mapping[str, Any]]) -> bool:
    return bool(candidates) and all(
        isinstance(candidate.get("snooze_window"), Mapping)
        and bool(candidate.get("snooze_window"))
        for candidate in candidates
    )


def _all_candidates_have_undo(candidates: list[Mapping[str, Any]]) -> bool:
    return bool(candidates) and all(
        bool(str(candidate.get("undo_scope") or "").strip())
        for candidate in candidates
    )


def _all_candidates_have_next_signal(candidates: list[Mapping[str, Any]]) -> bool:
    return bool(candidates) and all(
        bool(str(candidate.get("next_signal_required") or "").strip())
        for candidate in candidates
    )


def _observed_actions(interactions: list[Mapping[str, Any]]) -> list[str]:
    observed = {str(interaction.get("action") or "") for interaction in interactions}
    return [action for action in CONTROL_ACTIONS if action in observed]


def _empty_or_blocked(candidates: list[Mapping[str, Any]]) -> str:
    return "not_applicable" if not candidates else "blocked"


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_no_send_control_path_evidence",
]
