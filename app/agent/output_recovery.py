from __future__ import annotations

import re
from typing import Any


ACTION_ALIASES = {
    "clarify": "ask_user",
    "ask": "ask_user",
    "question": "ask_user",
    "search_then_answer": "search",
    "search_then_estimate": "search",
    "direct_estimate": "estimate",
    "estimate_now": "estimate",
    "estimate_kcal_with_assumptions": "estimate",
}


FOOD_TYPE_ALIASES = {
    "brand": "brand_item",
    "brand_food": "brand_item",
    "restaurant": "restaurant_item",
    "restaurant_food": "restaurant_item",
    "breakfast": "breakfast_shop",
    "breakfast_shop_item": "breakfast_shop",
    "home": "home_cooked",
    "homecooked": "home_cooked",
}


def exception_text(exc: Exception) -> str:
    text = str(exc).strip()
    return text or exc.__class__.__name__


def raw_preview(trace: dict[str, Any] | None, limit: int = 400) -> str | None:
    if not trace:
        return None
    raw = str(trace.get("raw_content") or "").strip()
    return raw[:limit] if raw else None


def normalize_action(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized:
        return None
    return ACTION_ALIASES.get(normalized, normalized)


def normalize_food_type(value: Any) -> str:
    if value is None:
        return "unknown"
    normalized = str(value).strip().lower()
    if not normalized:
        return "unknown"
    return FOOD_TYPE_ALIASES.get(normalized, normalized)


def is_empty_output(trace: dict[str, Any] | None) -> bool:
    if not trace:
        return False
    return str(trace.get("raw_content") or "").strip() == ""


def is_token_starved_empty(trace: dict[str, Any] | None) -> bool:
    if not trace or not is_empty_output(trace):
        return False
    finish_reason = str(trace.get("finish_reason") or "").strip().lower()
    try:
        completion_tokens = int(trace.get("completion_tokens") or 0)
    except (TypeError, ValueError):
        completion_tokens = 0
    return finish_reason == "length" and completion_tokens > 0


def is_provider_empty_stop(trace: dict[str, Any] | None) -> bool:
    if not trace or not is_empty_output(trace):
        return False
    finish_reason = str(trace.get("finish_reason") or "").strip().lower()
    try:
        completion_tokens = int(trace.get("completion_tokens") or 0)
    except (TypeError, ValueError):
        completion_tokens = 0
    return finish_reason == "stop" and completion_tokens == 0


def is_truncated_output(trace: dict[str, Any] | None) -> bool:
    if not trace:
        return False
    raw = str(trace.get("raw_content") or "").strip()
    return bool(raw) and raw.startswith("{") and not raw.endswith("}")


def is_transient_error(exc: Exception) -> bool:
    text = exception_text(exc).lower()
    return any(token in text for token in ["timeout", "tempor", "connection", "status=5"])


def coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    elif isinstance(value, dict):
        items = [value]
    else:
        text = str(value).strip()
        if not text:
            return []
        items = re.split(r"[,\n;]+", text)
    return [str(item).strip() for item in items if str(item).strip()]


def salvage_json_object(
    raw_content: str,
    *,
    string_fields: list[str],
    bool_fields: list[str],
    list_fields: list[str],
) -> dict[str, Any] | None:
    text = raw_content.strip()
    if not text or "{" not in text:
        return None
    snippet = text[text.find("{") :]
    fields: dict[str, Any] = {}

    for field in string_fields:
        match = re.search(rf'"{re.escape(field)}"\s*:\s*"([^"]*)"', snippet, flags=re.DOTALL)
        if match:
            fields[field] = match.group(1)

    for field in bool_fields:
        match = re.search(rf'"{re.escape(field)}"\s*:\s*(true|false)', snippet, flags=re.IGNORECASE)
        if match:
            fields[field] = match.group(1).lower() == "true"

    for field in list_fields:
        match = re.search(rf'"{re.escape(field)}"\s*:\s*\[(.*?)\]', snippet, flags=re.DOTALL)
        if match:
            inner = match.group(1).strip()
            fields[field] = re.findall(r'"([^"]*)"', inner) if inner else []

    if "ingredients" in list_fields:
        match = re.search(r'"ingredients"\s*:\s*\[(.*)', snippet, flags=re.DOTALL)
        if match and "ingredients" not in fields:
            fields["ingredients"] = []

    return fields or None
