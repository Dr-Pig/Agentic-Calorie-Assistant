from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable


def first_text(record: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = text(record.get(key))
        if value:
            return value
    return ""


def csv_value(record: dict[str, Any], *keys: str) -> str:
    normalized = {_normalize_key(key): value for key, value in record.items()}
    for key in keys:
        value = text(normalized.get(_normalize_key(key)))
        if value:
            return value
    return ""


def text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_key(value: Any) -> str:
    text = str(value or "").strip().casefold()
    return re.sub(r"[\s\-_()（）/]+", "", text)


def number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_amount_and_unit(value: str) -> tuple[float | None, str]:
    normalized = (
        text(value)
        .replace("毫升", "ml")
        .replace("公克", "g")
        .replace("Ｇ", "g")
        .replace("ｇ", "g")
        .replace("ＭＬ", "ml")
        .replace("ｍｌ", "ml")
    )
    match = re.search(r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z]+)", normalized)
    if not match:
        return None, ""
    return float(match.group("amount")), match.group("unit").casefold()


def split_aliases(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return dedupe(alias for item in value for alias in split_aliases(item))
    text = str(value).strip()
    if not text:
        return []
    for delimiter in ("、", "，", ",", ";", "；", "/"):
        text = text.replace(delimiter, "\n")
    return dedupe(part.strip() for part in text.splitlines() if part.strip())


def split_multivalue_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return dedupe(text(item) for item in value if text(item))
    text = str(value).strip()
    if not text:
        return []
    for delimiter in ("、", "，", ",", ";", "|"):
        text = text.replace(delimiter, "\n")
    return dedupe(part.strip() for part in text.splitlines() if part.strip())


def dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


__all__ = [
    "csv_value",
    "dedupe",
    "first_text",
    "number",
    "parse_amount_and_unit",
    "split_aliases",
    "split_multivalue_field",
    "stable_hash",
    "text",
]
