from __future__ import annotations

from typing import Any, Mapping


def exercise_budget(packet: Mapping[str, Any]) -> dict[str, Any]:
    budget = _mapping(packet.get("exercise_budget_packet"))
    if not budget:
        return {}
    return {
        "lab_exercise_event": dict(_mapping(budget.get("lab_exercise_event"))),
        "lab_ledger_entry": dict(_mapping(budget.get("lab_ledger_entry"))),
        "today_budget_projection": dict(_mapping(budget.get("today_budget_projection"))),
        "canonical_commit_requested": budget.get("canonical_commit_requested") is True,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["exercise_budget"]
