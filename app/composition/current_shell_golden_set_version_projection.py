from __future__ import annotations

from typing import Any


def old_version_superseded(
    phase_c_mutation: dict[str, Any],
    state_delta: dict[str, Any],
) -> bool | None:
    if state_delta.get("old_version_superseded") is not None:
        return bool(state_delta.get("old_version_superseded"))
    if phase_c_mutation.get("meal_version_delta") == "superseded_previous":
        return True
    canonical_ids = _dict(phase_c_mutation.get("canonical_ids"))
    if canonical_ids.get("superseded_version_id") is not None:
        return True
    return None


def ledger_delta_trace_present(
    phase_c_mutation: dict[str, Any],
    state_delta: dict[str, Any],
) -> bool:
    if state_delta.get("ledger_updated") is True:
        return True
    return phase_c_mutation.get("ledger_mutation_status") == "updated"


def old_version_not_counted(request_trace: dict[str, Any], state_delta: dict[str, Any]) -> bool | None:
    if state_delta.get("old_version_superseded") is not True:
        return None
    sidecar_today = _dict(_dict(_dict(request_trace.get("sidecar_output")).get("ui")).get("today"))
    meals = _list(sidecar_today.get("meals"))
    phase_c = _dict(request_trace.get("phase_c_trace"))
    mutation = _dict(phase_c.get("mutation_outcome"))
    superseded_id = _dict(mutation.get("canonical_ids")).get("superseded_version_id")
    if meals and superseded_id is not None:
        active_version_ids = {str(_dict(meal).get("meal_version_id")) for meal in meals}
        return str(superseded_id) not in active_version_ids
    same_truth = _dict(phase_c.get("same_truth_closure_gate")) or _dict(phase_c.get("same_truth_read_result"))
    if same_truth and same_truth.get("status") in {"pass", None}:
        return state_delta.get("ledger_updated") is True
    return None


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


__all__ = [
    "ledger_delta_trace_present",
    "old_version_not_counted",
    "old_version_superseded",
]
