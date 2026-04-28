from __future__ import annotations

import inspect
import json
from typing import Any, Awaitable


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def observed_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, tuple):
        return "tuple"
    return "unknown"


def value_excerpt(value: Any, *, max_chars: int = 1000) -> tuple[str, bool]:
    rendered = json.dumps(json_safe(value), ensure_ascii=False, default=str)
    if len(rendered) <= max_chars:
        return rendered, False
    return rendered[:max_chars], True


def tool_names(raw_tool_calls: Any) -> tuple[str, ...]:
    names: list[str] = []
    if not isinstance(raw_tool_calls, list):
        return tuple()
    for item in raw_tool_calls:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("tool_name") or "").strip()
        else:
            name = str(item or "").strip()
        if name:
            names.append(name)
    return tuple(names)


def tool_call_dicts(raw_tool_calls: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_tool_calls, list):
        return []
    result: list[dict[str, Any]] = []
    for item in raw_tool_calls:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("tool_name") or "").strip()
            arguments = item.get("arguments") if isinstance(item.get("arguments"), dict) else {}
        else:
            name = str(item or "").strip()
            arguments = {}
        if name:
            result.append({"name": name, "arguments": dict(arguments or {})})
    return result


async def maybe_await(value: Awaitable[Any] | Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value
