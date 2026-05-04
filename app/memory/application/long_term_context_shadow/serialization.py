from __future__ import annotations

import json
from typing import Any


def _redact_secret_values(value: Any) -> tuple[Any, list[str]]:
    redacted_fields: list[str] = []

    def redact(current: Any, path: str) -> Any:
        if isinstance(current, dict):
            result: dict[str, Any] = {}
            for key, item in current.items():
                key_text = str(key)
                child_path = f"{path}.{key_text}" if path else key_text
                if _is_secret_key(key_text):
                    result[key_text] = "[REDACTED]"
                    redacted_fields.append(child_path)
                else:
                    result[key_text] = redact(item, child_path)
            return result
        if isinstance(current, list):
            return [
                redact(item, f"{path}[{index}]") for index, item in enumerate(current)
            ]
        return current

    return redact(value, ""), redacted_fields


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(
        token in lowered
        for token in (
            "api_key",
            "apikey",
            "token",
            "secret",
            "password",
            "credential",
            "authorization",
        )
    )


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _slug(value: str) -> str:
    return "-".join(
        "".join(char.lower() if char.isalnum() else "-" for char in value).split("-")
    )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _model_dict(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json")


def _json_safe(value: Any) -> dict[str, Any]:
    payload = json.loads(json.dumps(value, ensure_ascii=False, default=str))
    if not isinstance(payload, dict):
        raise ValueError("Shadow lab artifact must be a JSON object")
    return payload
