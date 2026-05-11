from __future__ import annotations

from typing import Any, Mapping


def public_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "title": str(candidate.get("title") or ""),
        "source_type": str(candidate.get("source_type") or ""),
        "estimated_kcal_range": dict(_mapping(candidate.get("estimated_kcal_range"))),
        "quality_score": int(candidate.get("quality_score") or 0),
        "quality_tier": str(candidate.get("quality_tier") or ""),
        "proactive_intensity": str(candidate.get("proactive_intensity") or ""),
        "source_refs": [str(ref) for ref in candidate.get("source_refs") or []],
        "store_name": str(candidate.get("store_name") or ""),
        "location_area": str(candidate.get("location_area") or ""),
        "distance_m": _int_or_none(candidate.get("distance_m")),
    }


def candidate_explanation(candidate: Mapping[str, Any]) -> str:
    title = str(candidate.get("title") or "this option")
    return f"{title} fits the current budget and remembered preference context."


def remaining_kcal_from_retrieval(retrieval: Mapping[str, Any]) -> int | None:
    value = _mapping(retrieval.get("budget_posture")).get("remaining_kcal")
    return value if isinstance(value, int) else None


def candidate_by_id(
    candidates: list[Mapping[str, Any]],
    candidate_id: str,
) -> dict[str, Any] | None:
    for candidate in candidates:
        if str(candidate.get("candidate_id") or "") == candidate_id:
            return dict(candidate)
    return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


__all__ = [
    "candidate_by_id",
    "candidate_explanation",
    "public_candidate",
    "remaining_kcal_from_retrieval",
]
