from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = "Asia/Taipei"
_TAIPEI_FIXED_OFFSET = timezone(timedelta(hours=8), name=DEFAULT_TIMEZONE)
_WEEKDAY_MAP = {
    "一": 0,
    "二": 1,
    "三": 2,
    "四": 3,
    "五": 4,
    "六": 5,
    "日": 6,
    "天": 6,
}


def user_tz(tz_name: str | None = None) -> tzinfo:
    key = tz_name or DEFAULT_TIMEZONE
    try:
        return ZoneInfo(key)
    except Exception:
        if key == DEFAULT_TIMEZONE:
            return _TAIPEI_FIXED_OFFSET
        try:
            return ZoneInfo(DEFAULT_TIMEZONE)
        except Exception:
            return _TAIPEI_FIXED_OFFSET


def tz_key(tz: tzinfo, fallback: str | None = None) -> str:
    return getattr(tz, "key", None) or getattr(tz, "tzname", lambda _: None)(None) or fallback or DEFAULT_TIMEZONE


def parse_iso_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def relative_time_label(*, dt_utc: datetime | None, timezone_name: str | None = None, now_utc: datetime | None = None) -> str:
    if dt_utc is None:
        return ""
    tz = user_tz(timezone_name)
    current_utc = now_utc.astimezone(UTC) if now_utc else datetime.now(UTC)
    local_dt = dt_utc.astimezone(tz)
    local_now = current_utc.astimezone(tz)
    delta_days = (local_now.date() - local_dt.date()).days
    if delta_days <= 0:
        return "今天"
    if delta_days == 1:
        return "昨天"
    if delta_days == 2:
        return "前天"
    if delta_days == 30:
        return "30天前"
    if delta_days == 90:
        return "90天前"
    return f"{delta_days}天前"


def describe_time_fields(timestamp: str | None, *, timezone_name: str | None = None, now_utc: datetime | None = None) -> dict[str, str]:
    parsed = parse_iso_utc(timestamp)
    fallback_tz = user_tz(timezone_name)
    fallback_name = tz_key(fallback_tz, timezone_name or DEFAULT_TIMEZONE)
    if parsed is None:
        return {
            "occurred_at_utc": "",
            "occurred_at_local": "",
            "local_date": "",
            "timezone": fallback_name,
            "relative_time_label": "",
        }
    local_dt = parsed.astimezone(fallback_tz)
    return {
        "occurred_at_utc": parsed.isoformat(),
        "occurred_at_local": local_dt.isoformat(timespec="minutes"),
        "local_date": local_dt.date().isoformat(),
        "timezone": fallback_name,
        "relative_time_label": relative_time_label(dt_utc=parsed, timezone_name=fallback_name, now_utc=now_utc),
    }


def resolve_local_attribution(
    timestamp: str | datetime | None,
    *,
    timezone_name: str | None = None,
    fallback_local_date: str | None = None,
) -> dict[str, str | datetime | None]:
    fallback_tz = user_tz(timezone_name)
    fallback_name = tz_key(fallback_tz, timezone_name or DEFAULT_TIMEZONE)
    if isinstance(timestamp, datetime):
        parsed = timestamp.astimezone(UTC) if timestamp.tzinfo is not None else timestamp.replace(tzinfo=UTC)
    else:
        parsed = parse_iso_utc(timestamp)
    if parsed is None:
        return {
            "occurred_at": None,
            "occurred_at_utc": "",
            "occurred_at_local": "",
            "local_date": (fallback_local_date or "").strip(),
            "timezone": fallback_name,
        }
    local_dt = parsed.astimezone(fallback_tz)
    return {
        "occurred_at": parsed,
        "occurred_at_utc": parsed.isoformat(),
        "occurred_at_local": local_dt.isoformat(timespec="minutes"),
        "local_date": local_dt.date().isoformat(),
        "timezone": fallback_name,
    }


def infer_relative_date_target(text: str, *, timezone_name: str | None = None, now_utc: datetime | None = None) -> str | None:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return None
    tz = user_tz(timezone_name)
    local_now = (now_utc or datetime.now(UTC)).astimezone(tz)
    target = local_now.date()
    if "today" in normalized or "今天" in normalized:
        return target.isoformat()
    if "yesterday" in normalized or "昨天" in normalized:
        return (target - timedelta(days=1)).isoformat()
    if "前天" in normalized:
        return (target - timedelta(days=2)).isoformat()
    if "last tuesday" in normalized:
        weekday_token = 1
    elif "上週" in normalized or "上周" in normalized:
        weekday_token = None
        for token, weekday in _WEEKDAY_MAP.items():
            if f"上週{token}" in normalized or f"上周{token}" in normalized:
                weekday_token = weekday
                break
        if weekday_token is None:
            return None
    else:
        return None
    days_since_monday = target.weekday()
    this_week_monday = target - timedelta(days=days_since_monday)
    last_week_monday = this_week_monday - timedelta(days=7)
    return (last_week_monday + timedelta(days=weekday_token)).isoformat()
