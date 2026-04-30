from __future__ import annotations
from importlib import import_module
from typing import Any

__all__ = [
    "_normalize_intake_live_payload",
    "parse_weight_or_budget_intent",
]

_EXPORT_MAP = {
    "_normalize_intake_live_payload": (".intake_trace_tools", "_normalize_intake_live_payload"),
    "parse_weight_or_budget_intent": (".chat_intents", "parse_weight_or_budget_intent"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORT_MAP[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
