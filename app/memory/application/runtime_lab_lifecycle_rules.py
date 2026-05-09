from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping


PATTERN_MIN_COUNT = 5
PATTERN_ARCHIVE_AFTER_DAYS = 90
PATTERN_DELETE_AFTER_DAYS = 180


def pattern_lifecycle_decision(
    candidate: Mapping[str, Any],
    as_of: datetime,
) -> tuple[str, list[str]]:
    payload = _payload(candidate)
    last_seen_at = _parse_datetime(payload.get("last_seen_at"))
    if last_seen_at is not None:
        age_days = (as_of - last_seen_at).days
        if age_days >= PATTERN_DELETE_AFTER_DAYS:
            return "delete_review_candidate", ["pattern_delete_window_reached"]
        if age_days >= PATTERN_ARCHIVE_AFTER_DAYS:
            return "archive_review_candidate", ["pattern_archive_window_reached"]

    reinforcement_count = int(payload.get("reinforcement_count") or 0)
    if reinforcement_count >= PATTERN_MIN_COUNT:
        return "promotion_review_candidate", ["pattern_threshold_met"]
    return "hold_for_more_evidence", ["pattern_threshold_not_met"]


def temporary_preference_decision(
    candidate: Mapping[str, Any],
    as_of: datetime,
) -> tuple[str, list[str], str]:
    payload = _payload(candidate)
    created_at = _parse_datetime(payload.get("created_at"))
    default_max_days = int(payload.get("default_max_days") or 14)
    if created_at and (as_of - created_at).days >= default_max_days:
        return "expire_review_candidate", ["temporary_preference_expired"], "expired"
    return "hold_until_expiry_or_confirmation", ["temporary_preference_active"], "pending"


def negative_preference_decision(
    candidate: Mapping[str, Any],
) -> tuple[str, list[str], bool]:
    payload = _payload(candidate)
    if payload.get("confirmed") is True and payload.get("conflicts_with"):
        return (
            "contradiction_review_candidate",
            ["confirmed_negative_requires_review"],
            False,
        )
    return "human_confirmation_required", ["negative_preference_confirmation_required"], False


def default_preference_decision(candidate: Mapping[str, Any]) -> tuple[str, list[str]]:
    payload = _payload(candidate)
    if payload.get("llm_recommended_promotion") is True or payload.get(
        "promotion_allowed_now"
    ) is True:
        return "human_confirmation_required", ["llm_auto_promotion_blocked"]
    return "human_confirmation_required", ["human_confirmation_required"]


def parse_as_of(value: str) -> datetime:
    parsed = _parse_datetime(value)
    if parsed is None:
        raise ValueError("invalid_as_of")
    return parsed


def thresholds() -> dict[str, int]:
    return {
        "pattern_min_count": PATTERN_MIN_COUNT,
        "pattern_archive_after_days": PATTERN_ARCHIVE_AFTER_DAYS,
        "pattern_delete_after_days": PATTERN_DELETE_AFTER_DAYS,
    }


def _payload(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = candidate.get("payload")
    if isinstance(payload, Mapping):
        return payload
    return {}


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value)


__all__ = [
    "default_preference_decision",
    "negative_preference_decision",
    "parse_as_of",
    "pattern_lifecycle_decision",
    "temporary_preference_decision",
    "thresholds",
]
