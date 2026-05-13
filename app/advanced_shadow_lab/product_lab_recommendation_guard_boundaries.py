from __future__ import annotations

from typing import Any, Mapping


SOFT_PENALTY_SCORE_ADJUSTMENTS = {
    "negative_preference_downrank": -20,
}

REASON_FAMILIES = {
    "over_budget": "budget",
    "confirmed_negative_preference": "negative_preference",
    "memory_negative_preference_blocker": "negative_preference",
    "accepted_rescue_conflict": "rescue_conflict",
    "unavailable": "availability",
}


def candidate_guard_boundary_result(
    candidate: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    memory_negative_ids: list[str] | None = None,
) -> dict[str, Any]:
    hard_reason_codes: list[str] = []
    soft_penalty_codes: list[str] = []

    if _over_budget(candidate, payload):
        hard_reason_codes.append("over_budget")
    negative = _negative_preference_result(candidate, payload)
    hard_reason_codes.extend(negative["hard_reason_codes"])
    soft_penalty_codes.extend(negative["soft_penalty_codes"])
    if _matches_any_ref(candidate, memory_negative_ids or []):
        hard_reason_codes.append("memory_negative_preference_blocker")
    if _matches_any(candidate, _rescue_conflict_patterns(payload)):
        hard_reason_codes.append("accepted_rescue_conflict")
    hard_reason_codes.extend(_availability_reason_codes(candidate))

    hard_reason_codes = _unique(hard_reason_codes)
    soft_penalty_codes = _unique(soft_penalty_codes)
    return {
        "hard_reason_codes": hard_reason_codes,
        "soft_penalty_codes": soft_penalty_codes,
        "quality_score_adjustment": sum(
            SOFT_PENALTY_SCORE_ADJUSTMENTS.get(code, 0)
            for code in soft_penalty_codes
        ),
        "hard_blocker_trace": _trace(candidate, hard_reason_codes, hard=True),
        "soft_penalty_trace": _trace(candidate, soft_penalty_codes, hard=False),
    }


def _negative_preference_result(
    candidate: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, list[str]]:
    hard: list[str] = []
    soft: list[str] = []
    for item in _negative_preference_items(payload):
        if not _matches_any(candidate, [str(item.get("pattern") or "")]):
            continue
        status = str(item.get("status") or "")
        strength = str(item.get("strength") or "block")
        if status in {"allergy", "diet_constraint"} or strength == "block":
            hard.append("confirmed_negative_preference")
        elif status == "confirmed_negative_preference" and strength == "downrank":
            soft.append("negative_preference_downrank")
    return {"hard_reason_codes": _unique(hard), "soft_penalty_codes": _unique(soft)}


def _negative_preference_items(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    summary = _mapping(payload.get("negative_preference_summary"))
    return [
        item
        for item in summary.get("items", [])
        if isinstance(item, Mapping)
        and item.get("status") in {
            "confirmed_negative_preference",
            "allergy",
            "diet_constraint",
        }
    ]


def _availability_reason_codes(candidate: Mapping[str, Any]) -> list[str]:
    reasons = [
        str(flag)
        for flag in candidate.get("hard_avoid_flags", [])
        if str(flag)
    ]
    if candidate.get("availability_posture") == "unavailable":
        reasons.append("unavailable")
    return sorted(set(reasons))


def _over_budget(candidate: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    remaining = _int_field(_mapping(payload.get("current_budget_view")), "remaining_kcal")
    kcal_max = _int_field(_mapping(candidate.get("estimated_kcal_range")), "max")
    return remaining is not None and kcal_max is not None and kcal_max > remaining


def _rescue_conflict_patterns(payload: Mapping[str, Any]) -> list[str]:
    context = _mapping(payload.get("open_rescue_context"))
    return [str(item) for item in context.get("accepted_conflict_patterns", [])]


def _matches_any(candidate: Mapping[str, Any], patterns: list[str]) -> bool:
    title = _normalize(str(candidate.get("title", "")))
    tokens = {_normalize(str(item)) for item in candidate.get("item_patterns", [])}
    for pattern in patterns:
        normalized = _normalize(pattern)
        if normalized and (normalized in tokens or normalized in title):
            return True
    return False


def _matches_any_ref(candidate: Mapping[str, Any], candidate_ids: list[str]) -> bool:
    refs = [str(ref) for ref in candidate.get("source_refs", [])]
    return any(
        ref == candidate_id or ref.endswith(f":{candidate_id}")
        for ref in refs
        for candidate_id in candidate_ids
    )


def _trace(
    candidate: Mapping[str, Any],
    codes: list[str],
    *,
    hard: bool,
) -> list[dict[str, str | bool]]:
    return [
        {
            "candidate_id": str(candidate.get("candidate_id") or ""),
            "reason_code": code,
            "family": REASON_FAMILIES.get(code, "soft_preference"),
            "hard_blocker": hard,
            "source_node": "candidate_retrieval_guard_scoring",
        }
        for code in codes
    ]


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _int_field(mapping: Mapping[str, Any], key: str) -> int | None:
    value = mapping.get(key)
    return value if isinstance(value, int) else None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _normalize(value: str) -> str:
    return value.lower().replace(" ", "_").replace("-", "_")


__all__ = ["candidate_guard_boundary_result"]
