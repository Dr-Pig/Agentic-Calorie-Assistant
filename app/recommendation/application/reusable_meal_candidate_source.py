from __future__ import annotations

from typing import Any, Mapping


ALLOWED_REUSE_DECISIONS = {"reuse_exact", "reuse_anchored"}


def reusable_meal_candidate_source_projection(
    context: Mapping[str, Any],
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    omitted: list[dict[str, str]] = []
    for item in context.get("reusable_meal_candidates") or []:
        if not isinstance(item, Mapping):
            continue
        candidate, reason = _candidate(item)
        if candidate is None:
            omitted.append(
                {
                    "candidate_id": str(item.get("entity_id") or ""),
                    "source_family": "reusable_meal",
                    "reason": reason,
                }
            )
            continue
        candidates.append(candidate)
    return {
        "candidate_sources": candidates,
        "omitted_candidate_sources": omitted,
        "source_context_view": {
            "candidate_count": len(candidates),
            "omitted_count": len(omitted),
        },
    }


def _candidate(item: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str]:
    entity_id = str(item.get("entity_id") or "")
    drift_flags = _mapping(item.get("drift_flags"))
    if any(value is True for value in drift_flags.values()):
        return None, "reusable_meal_drift_requires_reestimate"
    if item.get("review_required") is True:
        return None, "reusable_meal_review_required"
    decision = str(item.get("estimate_posture_decision") or "")
    if decision not in ALLOWED_REUSE_DECISIONS:
        return None, f"reusable_meal_decision_not_recommendable:{decision or 'missing'}"
    estimated_kcal = _int_or_none(item.get("estimated_kcal"))
    kcal_range = _mapping(item.get("estimated_kcal_range"))
    if estimated_kcal is None and not kcal_range:
        return None, "reusable_meal_estimate_missing"
    return {
        "candidate_id": entity_id,
        "title": str(item.get("display_name") or entity_id),
        "source_family": "reusable_meal",
        "source_type": "reusable_meal_entity",
        "estimated_kcal": estimated_kcal,
        "estimated_kcal_range": dict(kcal_range),
        "evidence_posture": "exact" if decision == "reuse_exact" else "anchored",
        "availability_posture": "likely",
        "realistic_executable": True,
        "user_accessible": True,
        "item_patterns": _item_patterns(item),
        "hard_avoid_flags": [],
        "source_refs": [str(ref) for ref in item.get("source_refs") or []],
        "reusable_entity_id": entity_id,
        "drift_guard_status": "stable",
    }, ""


def _item_patterns(item: Mapping[str, Any]) -> list[str]:
    values = [
        str(item.get("normalized_signature") or ""),
        str(item.get("display_name") or "").lower().replace(" ", "_"),
    ]
    return [value for value in values if value]


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["reusable_meal_candidate_source_projection"]
