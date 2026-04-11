from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "LoadedConversationContext",
    "load_conversation_state",
]

_EXPORT_MAP = {
    "LoadedConversationContext": (".conversation_state_loader", "LoadedConversationContext"),
    "load_conversation_state": (".conversation_state_loader", "load_conversation_state"),
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
