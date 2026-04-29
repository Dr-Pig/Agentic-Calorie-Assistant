from __future__ import annotations

from typing import Any


_MUTATION_KEYS = (
    "meal_logged",
    "canonical_commit",
    "draft_saved",
    "new_meal_version_created",
    "old_version_superseded",
    "ledger_updated",
)


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _bool_field(surface: dict[str, Any], key: str) -> bool | None:
    if key not in surface:
        return None
    return bool(surface.get(key))


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _canonical_commit(persistence_result: Any | None) -> dict[str, Any] | None:
    commit = _field(persistence_result, "canonical_commit") if persistence_result is not None else None
    return dict(commit) if isinstance(commit, dict) else None


def _canonical_ids(*, persistence_result: Any | None, canonical_commit: dict[str, Any] | None) -> dict[str, Any]:
    commit = canonical_commit or {}
    return {
        "meal_thread_id": commit.get("meal_thread_id"),
        "meal_version_id": commit.get("meal_version_id"),
        "meal_id": commit.get("meal_id"),
        "superseded_version_id": commit.get("superseded_version_id"),
        "persisted_log_id": _field(persistence_result, "persisted_log_id"),
        "linked_meal_log_id": _field(persistence_result, "linked_meal_log_id"),
    }


def _commit_status(
    *,
    persistence_result: Any | None,
    canonical_commit: dict[str, Any] | None,
    state_delta: dict[str, Any],
    sidecar_summary: dict[str, Any],
) -> str:
    state_commit = _bool_field(state_delta, "canonical_commit")
    sidecar_commit = _bool_field(sidecar_summary, "canonical_commit")
    if canonical_commit is not None:
        if state_commit is False or sidecar_commit is False:
            return "contradictory"
        return "committed"
    if state_commit is True or sidecar_commit is True:
        return "contradictory"
    if state_commit is False or sidecar_commit is False:
        return "not_committed"
    if persistence_result is not None:
        return "not_committed"
    return "not_available"


def _ledger_status(
    *,
    canonical_commit_status: str,
    state_delta: dict[str, Any],
    sidecar_summary: dict[str, Any],
) -> str:
    state_ledger = _bool_field(state_delta, "ledger_updated")
    sidecar_ledger = _bool_field(sidecar_summary, "ledger_updated")
    if state_ledger is True or sidecar_ledger is True:
        if canonical_commit_status != "committed":
            return "contradictory"
        if state_ledger is False or sidecar_ledger is False:
            return "contradictory"
        return "updated"
    if state_ledger is False or sidecar_ledger is False:
        if canonical_commit_status == "committed":
            return "contradictory"
        return "not_updated"
    return "not_available"


def _meal_version_delta(
    *,
    canonical_commit: dict[str, Any] | None,
    state_delta: dict[str, Any],
    sidecar_summary: dict[str, Any],
) -> str:
    state_new = _bool_field(state_delta, "new_meal_version_created")
    state_superseded = _bool_field(state_delta, "old_version_superseded")
    sidecar_new = _bool_field(sidecar_summary, "new_meal_version_created")
    sidecar_superseded = _bool_field(sidecar_summary, "old_version_superseded")
    commit_has_version = bool((canonical_commit or {}).get("meal_version_id"))
    commit_has_superseded = bool((canonical_commit or {}).get("superseded_version_id"))

    if commit_has_superseded:
        if state_superseded is False or sidecar_superseded is False:
            return "contradictory"
        return "superseded_previous"
    if commit_has_version:
        if state_new is False or sidecar_new is False:
            return "contradictory"
        return "new_version_created"
    if state_superseded is True or sidecar_superseded is True:
        return "contradictory"
    if state_new is True or sidecar_new is True:
        return "contradictory"
    if state_new is False or sidecar_new is False or state_superseded is False or sidecar_superseded is False:
        return "none"
    return "not_available"


def _draft_status(*, state_delta: dict[str, Any], sidecar_summary: dict[str, Any]) -> str:
    state_draft = _bool_field(state_delta, "draft_saved")
    sidecar_draft = _bool_field(sidecar_summary, "draft_saved")
    if state_draft is True or sidecar_draft is True:
        if state_draft is False or sidecar_draft is False:
            return "contradictory"
        return "saved"
    if state_draft is False or sidecar_draft is False:
        return "not_saved"
    return "not_available"


def _macro_status(sidecar: dict[str, Any]) -> str:
    macro = _dict(sidecar.get("macro"))
    display_status = str(macro.get("display_status") or "").strip()
    if display_status == "show":
        return "visible"
    if display_status == "hide":
        return "hidden"
    return "not_available"


def _phase_a_commit_intent(phase_a_trace: dict[str, Any]) -> str | None:
    projection = _dict(phase_a_trace.get("boundary_projection"))
    decision = _dict(projection.get("commit_boundary_decision"))
    intent = decision.get("intent")
    return str(intent) if intent is not None else None


def _compared_surfaces(
    *,
    persistence_result: Any | None,
    state_delta: dict[str, Any],
    sidecar_summary: dict[str, Any],
    sidecar: dict[str, Any],
    phase_a_trace: dict[str, Any],
    budget_summary: dict[str, Any] | None,
) -> list[str]:
    surfaces: list[str] = []
    if persistence_result is not None:
        surfaces.append("persistence_result")
    if state_delta:
        surfaces.append("state_delta")
    if sidecar_summary:
        surfaces.append("sidecar.state_mutation_summary")
    if _dict(sidecar.get("macro")):
        surfaces.append("sidecar.macro")
    if _dict(phase_a_trace.get("boundary_projection")):
        surfaces.append("phase_a_trace.boundary_projection")
    if budget_summary is not None:
        surfaces.append("budget_summary")
    return surfaces


def _consistency_flags(
    *,
    canonical_commit: dict[str, Any] | None,
    canonical_commit_status: str,
    ledger_mutation_status: str,
    macro_visibility_status: str,
    state_delta: dict[str, Any],
    sidecar_summary: dict[str, Any],
    phase_a_commit_intent: str | None,
) -> list[str]:
    flags: list[str] = []
    state_commit = _bool_field(state_delta, "canonical_commit")
    sidecar_commit = _bool_field(sidecar_summary, "canonical_commit")
    if (state_commit is True and canonical_commit is None) or (state_commit is False and canonical_commit is not None):
        flags.append("state_delta_persistence_commit_mismatch")
    if (sidecar_commit is True and canonical_commit is None) or (sidecar_commit is False and canonical_commit is not None):
        flags.append("sidecar_persistence_commit_mismatch")
    for key in _MUTATION_KEYS:
        state_value = _bool_field(state_delta, key)
        sidecar_value = _bool_field(sidecar_summary, key)
        if state_value is not None and sidecar_value is not None and state_value != sidecar_value:
            flags.append("state_delta_sidecar_mutation_mismatch")
            break
    if ledger_mutation_status == "contradictory":
        flags.append("ledger_commit_mismatch")
    if macro_visibility_status == "visible" and canonical_commit_status != "committed":
        flags.append("macro_visible_without_commit")
    if phase_a_commit_intent == "draft" and canonical_commit_status == "committed":
        flags.append("phase_a_projection_commit_mismatch")
    if phase_a_commit_intent == "commit" and canonical_commit_status == "not_committed":
        flags.append("phase_a_projection_commit_mismatch")
    return flags


def build_phase_c_trace(
    *,
    persistence_result: Any | None,
    state_delta: dict[str, Any] | None,
    sidecar: dict[str, Any] | None,
    phase_a_trace: dict[str, Any] | None,
    budget_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    state_delta_dict = _dict(state_delta)
    sidecar_dict = _dict(sidecar)
    sidecar_summary = _dict(sidecar_dict.get("state_mutation_summary"))
    phase_a_trace_dict = _dict(phase_a_trace)
    canonical_commit = _canonical_commit(persistence_result)
    canonical_commit_status = _commit_status(
        persistence_result=persistence_result,
        canonical_commit=canonical_commit,
        state_delta=state_delta_dict,
        sidecar_summary=sidecar_summary,
    )
    ledger_mutation_status = _ledger_status(
        canonical_commit_status=canonical_commit_status,
        state_delta=state_delta_dict,
        sidecar_summary=sidecar_summary,
    )
    meal_version_delta = _meal_version_delta(
        canonical_commit=canonical_commit,
        state_delta=state_delta_dict,
        sidecar_summary=sidecar_summary,
    )
    macro_visibility_status = _macro_status(sidecar_dict)
    phase_a_intent = _phase_a_commit_intent(phase_a_trace_dict)
    compared_surfaces = _compared_surfaces(
        persistence_result=persistence_result,
        state_delta=state_delta_dict,
        sidecar_summary=sidecar_summary,
        sidecar=sidecar_dict,
        phase_a_trace=phase_a_trace_dict,
        budget_summary=budget_summary,
    )
    flags = _consistency_flags(
        canonical_commit=canonical_commit,
        canonical_commit_status=canonical_commit_status,
        ledger_mutation_status=ledger_mutation_status,
        macro_visibility_status=macro_visibility_status,
        state_delta=state_delta_dict,
        sidecar_summary=sidecar_summary,
        phase_a_commit_intent=phase_a_intent,
    )
    owner_alignment = "not_applicable" if not compared_surfaces else "contradictory" if flags else "aligned"
    return {
        "mutation_outcome": {
            "canonical_commit_status": canonical_commit_status,
            "draft_status": _draft_status(state_delta=state_delta_dict, sidecar_summary=sidecar_summary),
            "ledger_mutation_status": ledger_mutation_status,
            "meal_version_delta": meal_version_delta,
            "macro_visibility_status": macro_visibility_status,
            "persistence_action": _field(persistence_result, "action"),
            "canonical_ids": _canonical_ids(
                persistence_result=persistence_result,
                canonical_commit=canonical_commit,
            ),
        },
        "same_truth_read_result": {
            "owner_alignment": owner_alignment,
            "consistency_flags": flags,
            "compared_surfaces": compared_surfaces,
            "phase_a_projected_commit_intent": phase_a_intent,
        },
    }


__all__ = ["build_phase_c_trace"]
