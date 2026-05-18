from __future__ import annotations

from typing import Any

from app.intake.application.manager_context_policy_constants import (
    TARGET_CANDIDATE_BOOL_FIELDS,
    TARGET_CANDIDATE_FIELDS,
)


def target_candidates(
    candidates: list[dict[str, Any]],
    *,
    max_target_candidates: int,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for candidate in list(candidates or []):
        if len(normalized) >= max_target_candidates:
            break
        if not isinstance(candidate, dict):
            continue
        if str(candidate.get("target_object_type") or "") == "pending_followup":
            continue
        item = {
            key: candidate[key]
            for key in TARGET_CANDIDATE_FIELDS
            if key in candidate and _safe_scalar(candidate[key])
        }
        if (
            item.get("target_object_type") == "meal_thread"
            and item.get("meal_thread_id") in (None, "")
            and item.get("target_object_id") not in (None, "")
        ):
            item["meal_thread_id"] = item["target_object_id"]
        if (
            item.get("target_object_type") in {"meal_thread", "meal_item", "meal_item_candidate"}
            and item.get("target_display_name") in (None, "")
            and item.get("display_name") not in (None, "")
        ):
            item["target_display_name"] = item["display_name"]
        for key in TARGET_CANDIDATE_BOOL_FIELDS:
            if isinstance(candidate.get(key), bool):
                item[key] = candidate[key]
        item.setdefault("uniqueness_status", "candidate")
        item["read_only"] = True
        item["mutation_authority"] = False
        normalized.append(item)
    return normalized


def _safe_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float)) and not isinstance(value, bool)


__all__ = ["target_candidates"]
