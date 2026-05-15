from __future__ import annotations

from typing import Any


def attach_implausible_kcal_conflict_outcome(
    *,
    runtime: dict[str, Any],
    manager_final: dict[str, Any],
    manager_decision: dict[str, Any],
    workflow_effect: Any,
    final_action: Any,
    mutation_allowed: bool | None,
) -> None:
    if not _manager_named_food_kcal_conflict(manager_final, manager_decision):
        return
    if mutation_allowed is not False:
        return
    if str(final_action or workflow_effect or "") != "ask_followup":
        return
    runtime.setdefault("silent_accept_implausible_kcal_allowed", False)
    runtime.setdefault("override_with_system_estimate_allowed", False)


def _manager_named_food_kcal_conflict(
    manager_final: dict[str, Any],
    manager_decision: dict[str, Any],
) -> bool:
    semantic_decision = _dict(manager_final.get("semantic_decision")) or _dict(
        manager_decision.get("semantic_decision")
    )
    source = str(semantic_decision.get("source") or manager_final.get("source") or "")
    return source == "named_food_user_kcal_conflict"


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


__all__ = ["attach_implausible_kcal_conflict_outcome"]
