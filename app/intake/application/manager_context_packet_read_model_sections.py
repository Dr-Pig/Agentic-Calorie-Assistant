from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.runtime.contracts.phase_a import CurrentTurnContextV1


def read_model_summary(current_turn_context: CurrentTurnContextV1) -> dict[str, Any]:
    return {
        "budget": _readonly_copy(current_turn_context.current_budget_snapshot) or {},
        "body_plan": _readonly_copy(current_turn_context.active_body_plan_snapshot) or {},
        "current_day": {
            "active_meal_thread_ref": _readonly_copy(current_turn_context.active_meal_thread_ref),
            "open_workflow_type": current_turn_context.open_workflow_type,
            "read_only": True,
            "mutation_authority": False,
        },
        "recent_committed_meals": [
            _readonly_copy(meal) for meal in list(current_turn_context.recent_committed_meal_refs or [])
        ],
        "read_only": True,
        "mutation_authority": False,
    }


def evidence_state(value: dict[str, Any] | None) -> dict[str, Any]:
    state = dict(value or {})
    return {
        "fooddb": _readonly_mapping(state.get("fooddb")),
        "websearch": _readonly_mapping(state.get("websearch")),
        "macro": _readonly_mapping(state.get("macro")),
        "selected_extracts": _readonly_list(state.get("selected_extracts")),
        "rejected_candidates": _readonly_list(state.get("rejected_candidates")),
        "read_only": True,
        "mutation_authority": False,
        "selection_owner": "manager",
    }


def _readonly_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"read_only": True, "mutation_authority": False}
    copied = _readonly_copy(value)
    return copied if isinstance(copied, dict) else {"read_only": True, "mutation_authority": False}


def _readonly_list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return []
    return [_readonly_copy(item) for item in value]


def _readonly_copy(value: Any) -> Any:
    if value is None:
        return None
    copied = deepcopy(value)
    if isinstance(copied, dict):
        copied["read_only"] = True
        copied["mutation_authority"] = False
    return copied


__all__ = ["evidence_state", "read_model_summary"]
