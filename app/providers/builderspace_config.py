from __future__ import annotations

import json
from typing import Any

from ..text_integrity import corruption_summary, find_text_corruption
from .builderspace_parsing import jsonable


PLACEHOLDER_VALUES = {"", "replace-me", "https://api.example.com"}
DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 120


def format_user_message(stage: str, user_payload: dict[str, Any]) -> str:
    return json.dumps({"stage": stage, "payload": jsonable(user_payload)}, ensure_ascii=False)


def check_encoding_safety(content: str) -> None:
    findings = find_text_corruption(content)
    if findings:
        summary = corruption_summary(findings)
        raise RuntimeError(f"Encoding Gate Failure (Layer 1): text corruption detected before serialization: {summary}")


def has_real_value(value: str) -> bool:
    normalized = value.strip()
    if not normalized:
        return False
    if normalized in PLACEHOLDER_VALUES:
        return False
    if normalized.endswith("example.com"):
        return False
    return True


def is_configured(*, base_url: str, token: str, manager_model: str) -> bool:
    return has_real_value(base_url) and has_real_value(token) and has_real_value(manager_model)


def effective_timeout_seconds(raw_value: str | None) -> tuple[int, bool]:
    if raw_value in (None, ""):
        return DEFAULT_TIMEOUT_SECONDS, False
    try:
        parsed = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_SECONDS, False
    if parsed <= 0:
        return DEFAULT_TIMEOUT_SECONDS, False
    if parsed > MAX_TIMEOUT_SECONDS:
        return MAX_TIMEOUT_SECONDS, True
    return parsed, False
