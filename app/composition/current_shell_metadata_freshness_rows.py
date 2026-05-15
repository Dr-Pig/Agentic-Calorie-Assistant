from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _age_hours(generated_at_utc: Any, *, now: datetime) -> float | None:
    parsed = _parse_timestamp(generated_at_utc)
    if parsed is None:
        return None
    return (now - parsed).total_seconds() / 3600


def metadata_row(
    group_id: str,
    payload: dict[str, Any],
    *,
    now: datetime,
    max_age_hours: int,
    present: bool,
) -> dict[str, Any]:
    age = _age_hours(payload.get("generated_at_utc"), now=now)
    if age is None:
        freshness_status = "invalid_timestamp"
    elif age < 0:
        freshness_status = "future"
    elif age > max_age_hours:
        freshness_status = "stale"
    else:
        freshness_status = "fresh"
    return {
        "group_id": group_id,
        "artifact_path": payload.get("artifact_path", "not_available"),
        "present": present,
        "artifact_type": payload.get("artifact_type", "not_available"),
        "artifact_schema_version": payload.get("artifact_schema_version", "not_available"),
        "status": payload.get("status", "not_available"),
        "generated_at_utc": payload.get("generated_at_utc", "not_available"),
        "file_mtime_utc": payload.get("file_mtime_utc", "not_available"),
        "age_hours": round(age, 3) if age is not None else "not_available",
        "freshness_status": freshness_status,
    }
