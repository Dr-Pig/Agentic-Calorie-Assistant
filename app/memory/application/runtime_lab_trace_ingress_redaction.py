from __future__ import annotations

import re
from typing import Any

from app.memory.application.long_term_context_shadow.serialization import (
    _redact_secret_values,
)


_SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(sk-(?:live|test)-[A-Za-z0-9_-]+|tok_(?:live|test|secret)[A-Za-z0-9_-]*)"
)


def sanitize_trace(trace: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    redacted_by_key, key_fields = _redact_secret_values(trace)
    redacted_by_value, value_fields = _redact_secret_text(redacted_by_key)
    return redacted_by_value, [*key_fields, *value_fields]


def _redact_secret_text(value: Any, path: str = "") -> tuple[Any, list[str]]:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        fields: list[str] = []
        for key, item in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            redacted, child_fields = _redact_secret_text(item, child_path)
            result[key] = redacted
            fields.extend(child_fields)
        return result, fields
    if isinstance(value, list):
        result_list: list[Any] = []
        fields = []
        for index, item in enumerate(value):
            redacted, child_fields = _redact_secret_text(item, f"{path}[{index}]")
            result_list.append(redacted)
            fields.extend(child_fields)
        return result_list, fields
    if isinstance(value, str) and _SECRET_VALUE_PATTERN.search(value):
        return _SECRET_VALUE_PATTERN.sub("[REDACTED]", value), [path]
    return value, []


__all__ = ["sanitize_trace"]
