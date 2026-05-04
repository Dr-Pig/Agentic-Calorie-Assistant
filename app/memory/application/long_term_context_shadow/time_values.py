from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any


def _time_bucket(value: Any) -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        return "unknown"
    hour = parsed.hour
    if 5 <= hour < 11:
        return "morning"
    if 11 <= hour < 15:
        return "midday"
    if 15 <= hour < 20:
        return "evening"
    return "late"


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_date_as_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    parsed = _parse_datetime(value)
    if parsed:
        return parsed
    try:
        return datetime.fromisoformat(str(value) + "T00:00:00+00:00")
    except ValueError:
        return None


def _most_common(counter: Counter[str]) -> tuple[str, int]:
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0]


def _confidence(count: int, *, threshold: int) -> float:
    if threshold <= 0:
        return 0.0
    return min(1.0, round(count / threshold, 2))


def _bounded_confidence(value: Any, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0.0, min(1.0, round(parsed, 2)))


def _float_value(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _token_estimate(text: str) -> int:
    return max(0, len(text) // 4)
