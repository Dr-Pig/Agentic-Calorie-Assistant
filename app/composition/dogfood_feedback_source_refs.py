from __future__ import annotations

from typing import Any


def _clean(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def build_feedback_source_refs(
    *,
    request_id: Any = None,
    trace_id: Any = None,
    message_id: Any = None,
    meal_id: Any = None,
) -> list[str]:
    refs: list[str] = []
    for prefix, value in (
        ("request", request_id),
        ("trace", trace_id),
        ("message", message_id),
        ("meal", meal_id),
    ):
        cleaned = _clean(value)
        if cleaned:
            refs.append(f"{prefix}:{cleaned}")
    return refs
