from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "RescueOverlayTargetDay",
    "apply_rescue_chat_action",
    "assess_rescue_overlay_day",
    "build_open_rescue_proposals_view",
    "build_rescue_chat_surface",
    "build_rescue_proposal",
    "build_rescue_response_result",
    "build_rescue_runtime_artifact",
    "persist_rescue_runtime_artifact",
    "should_surface_rescue_response",
]

_EXPORT_MAP = {
    "RescueOverlayTargetDay": (".overlay", "RescueOverlayTargetDay"),
    "apply_rescue_chat_action": (".chat_surface", "apply_rescue_chat_action"),
    "assess_rescue_overlay_day": (".overlay", "assess_rescue_overlay_day"),
    "build_open_rescue_proposals_view": (".open_proposals_read_model", "build_open_rescue_proposals_view"),
    "build_rescue_chat_surface": (".chat_surface", "build_rescue_chat_surface"),
    "build_rescue_proposal": (".proposal", "build_rescue_proposal"),
    "build_rescue_response_result": (".response", "build_rescue_response_result"),
    "build_rescue_runtime_artifact": (".runtime", "build_rescue_runtime_artifact"),
    "persist_rescue_runtime_artifact": (".runtime", "persist_rescue_runtime_artifact"),
    "should_surface_rescue_response": (".response", "should_surface_rescue_response"),
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
