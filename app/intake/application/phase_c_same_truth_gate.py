from __future__ import annotations

from typing import Any


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _model_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dict(dumped) if isinstance(dumped, dict) else {}
    return {}


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool_field(surface: dict[str, Any], key: str) -> bool | None:
    if key not in surface:
        return None
    return bool(surface.get(key))


def _append_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _phase_c_surfaces(phase_c_trace: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return _dict(phase_c_trace.get("mutation_outcome")), _dict(phase_c_trace.get("same_truth_read_result"))


def _current_budget_view(state_after: Any | None) -> dict[str, Any]:
    return _model_dict(_field(state_after, "current_budget_view"))


def build_phase_c_same_truth_gate(
    *,
    phase_c_trace: dict[str, Any] | None,
    persistence_result: Any | None,
    state_delta: dict[str, Any] | None,
    sidecar: dict[str, Any] | None,
    state_after: Any | None,
    budget_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    trace = _dict(phase_c_trace)
    mutation_outcome, read_result = _phase_c_surfaces(trace)
    state_delta_dict = _dict(state_delta)
    sidecar_summary = _dict(_dict(sidecar).get("state_mutation_summary"))
    budget_after = _current_budget_view(state_after)
    compared_surfaces = list(read_result.get("compared_surfaces") or [])
    consistency_flags = list(read_result.get("consistency_flags") or [])

    if not mutation_outcome or not read_result:
        _append_once(consistency_flags, "phase_c_trace_not_available")
    if persistence_result is not None:
        _append_once(compared_surfaces, "persistence_result")
    if state_delta_dict:
        _append_once(compared_surfaces, "state_delta")
    if sidecar_summary:
        _append_once(compared_surfaces, "sidecar.state_mutation_summary")
    if budget_after:
        _append_once(compared_surfaces, "state_after.current_budget_view")
    if budget_summary is not None:
        _append_once(compared_surfaces, "budget_summary")

    canonical_commit = _field(persistence_result, "canonical_commit") if persistence_result is not None else None
    projected_commit = mutation_outcome.get("canonical_commit_status")
    if canonical_commit is not None and projected_commit not in {"committed", None}:
        _append_once(consistency_flags, "phase_c_projection_persistence_commit_mismatch")
    if canonical_commit is None and projected_commit == "committed":
        _append_once(consistency_flags, "phase_c_projection_persistence_commit_mismatch")

    state_commit = _bool_field(state_delta_dict, "canonical_commit")
    sidecar_commit = _bool_field(sidecar_summary, "canonical_commit")
    if state_commit is not None and sidecar_commit is not None and state_commit != sidecar_commit:
        _append_once(consistency_flags, "state_delta_sidecar_mutation_mismatch")

    canonical_ids = _dict(mutation_outcome.get("canonical_ids"))
    committed_thread_id = _int_or_none(canonical_ids.get("meal_thread_id"))
    committed_version_id = _int_or_none(canonical_ids.get("meal_version_id"))
    if committed_thread_id is None and isinstance(canonical_commit, dict):
        committed_thread_id = _int_or_none(canonical_commit.get("meal_thread_id"))
    if committed_version_id is None and isinstance(canonical_commit, dict):
        committed_version_id = _int_or_none(canonical_commit.get("meal_version_id"))
    if committed_thread_id is not None and committed_version_id is not None and isinstance(budget_after.get("meals"), list):
        matching_meals = [
            meal
            for meal in budget_after.get("meals", [])
            if isinstance(meal, dict) and _int_or_none(meal.get("meal_thread_id")) == committed_thread_id
        ]
        if matching_meals and all(_int_or_none(meal.get("meal_version_id")) != committed_version_id for meal in matching_meals):
            _append_once(consistency_flags, "canonical_active_version_mismatch")

    predicted_consumed = _int_or_none(_field(budget_summary, "predicted_consumed_kcal_after"))
    predicted_remaining = _int_or_none(_field(budget_summary, "predicted_remaining_kcal_after"))
    read_consumed = _int_or_none(budget_after.get("consumed_kcal"))
    read_remaining = _int_or_none(budget_after.get("remaining_kcal"))
    if (
        (predicted_consumed is not None and read_consumed is not None and predicted_consumed != read_consumed)
        or (predicted_remaining is not None and read_remaining is not None and predicted_remaining != read_remaining)
    ):
        _append_once(consistency_flags, "budget_summary_state_after_mismatch")

    hard_fail = (
        read_result.get("owner_alignment") == "contradictory"
        or "contradictory" in set(str(value) for value in mutation_outcome.values())
        or "budget_summary_state_after_mismatch" in consistency_flags
        or "canonical_active_version_mismatch" in consistency_flags
        or "phase_c_projection_persistence_commit_mismatch" in consistency_flags
        or "state_delta_sidecar_mutation_mismatch" in consistency_flags
    )
    if hard_fail:
        status = "hard_fail"
        failure_family = "phase_c_same_truth_contradiction"
    elif consistency_flags:
        status = "flagged"
        failure_family = None
    else:
        status = "pass"
        failure_family = None

    return {
        "checked": True,
        "status": status,
        "failure_family": failure_family,
        "consistency_flags": consistency_flags,
        "compared_surfaces": compared_surfaces,
    }


__all__ = ["build_phase_c_same_truth_gate"]
