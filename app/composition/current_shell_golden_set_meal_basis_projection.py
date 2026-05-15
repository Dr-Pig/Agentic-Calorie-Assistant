from __future__ import annotations

from typing import Any


def meal_level_basis_visible(request_trace: dict[str, Any]) -> bool | None:
    basis = _dict(request_trace.get("renderer_input_basis"))
    state_after = _dict(basis.get("state_after")) or _dict(request_trace.get("state_after"))
    active_meal = _dict(state_after.get("active_meal"))
    candidates = _list(active_meal.get("item_candidates"))
    if candidates:
        return True
    return None


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []
