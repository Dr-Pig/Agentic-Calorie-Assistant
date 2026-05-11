from __future__ import annotations

from typing import Any, Mapping


def premeal_enabled(turn: Mapping[str, Any]) -> bool:
    return turn.get("turn_mode") == "pre_meal_planning"


def premeal_context(
    *,
    turn: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    if not premeal_enabled(turn):
        return {}
    source = _mapping(payload.get("pre_meal_planning_context"))
    location_area = str(turn.get("location_area") or source.get("location_area") or "")
    location_requested = bool(location_area.strip())
    return {
        "mode": "pre_meal_planning",
        "location_requested": location_requested,
        "location_area": location_area,
        "location_source": "structured_turn" if location_requested else "",
        "location_fallback_reason": ""
        if location_requested
        else "location_unavailable_fallback_to_preferences",
        "budget_source": str(source.get("budget_source") or "current_budget_view.remaining_kcal"),
        "preference_source_refs": [
            str(ref) for ref in source.get("preference_source_refs") or []
        ],
    }


def premeal_candidate_filter_reason(
    candidate: Mapping[str, Any],
    context: Mapping[str, Any],
) -> list[str]:
    if context.get("mode") != "pre_meal_planning":
        return []
    if context.get("location_requested") is not True:
        return []
    expected = str(context.get("location_area") or "")
    actual = str(candidate.get("location_area") or "")
    return [] if actual == expected else ["location_mismatch"]


def premeal_packet(
    *,
    primary_candidate: Mapping[str, Any],
    context: Mapping[str, Any],
    remaining_kcal: int | None,
) -> dict[str, Any]:
    if context.get("mode") != "pre_meal_planning":
        return {}
    kcal = _mapping(primary_candidate.get("estimated_kcal_range"))
    min_kcal = _int(kcal.get("min"))
    max_kcal = _int(kcal.get("max"))
    return {
        "mode": "pre_meal_planning",
        "selected_place": {
            "candidate_id": str(primary_candidate.get("candidate_id") or ""),
            "store_name": str(primary_candidate.get("store_name") or ""),
            "location_area": str(primary_candidate.get("location_area") or ""),
            "distance_m": _int(primary_candidate.get("distance_m")),
        },
        "suggested_kcal_range": {"min": min_kcal, "max": max_kcal},
        "remaining_kcal_after_primary_range": _remaining_after(
            remaining_kcal,
            min_kcal,
            max_kcal,
        ),
        "location_fallback_reason": str(context.get("location_fallback_reason") or ""),
        "budget_allocation_advice": (
            f"Keep this meal around {min_kcal}-{max_kcal} kcal; "
            f"you should still have {remaining_kcal - max_kcal}-{remaining_kcal - min_kcal} kcal."
        )
        if remaining_kcal is not None
        else "",
        "canonical_commit_requested": False,
    }


def _remaining_after(
    remaining_kcal: int | None,
    min_kcal: int,
    max_kcal: int,
) -> dict[str, int | None]:
    if remaining_kcal is None:
        return {"min": None, "max": None}
    return {"min": remaining_kcal - max_kcal, "max": remaining_kcal - min_kcal}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = [
    "premeal_candidate_filter_reason",
    "premeal_context",
    "premeal_enabled",
    "premeal_packet",
]
