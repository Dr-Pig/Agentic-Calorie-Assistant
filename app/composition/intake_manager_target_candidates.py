from __future__ import annotations

from typing import Any


def thread_target_candidates(correction_target: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in correction_target.get("thread_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        meal_thread_id = candidate.get("meal_thread_id")
        if meal_thread_id is None:
            continue
        key = str(meal_thread_id)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(dict(candidate))
    meal_thread_id = correction_target.get("meal_thread_id")
    if meal_thread_id is not None and str(meal_thread_id) not in seen:
        candidates.append(
            {
                "meal_thread_id": meal_thread_id,
                "meal_version_id": correction_target.get("meal_version_id"),
                "meal_title": correction_target.get("meal_title"),
            }
        )
    return candidates
