from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "RescueOverlayDayAssessment",
    "RescueOverlayTargetDay",
    "ShortHorizonRescuePlan",
    "apply_short_horizon_rescue_plan",
    "assess_rescue_overlay_day",
    "build_planner_context_payload",
    "build_short_horizon_rescue_plan",
    "fallback_planner_result",
    "normalize_planner_result",
    "planner_enabled",
    "render_conversation_state_prompt",
]

_EXPORT_MAP = {
    "build_planner_context_payload": (".context_assembly", "build_planner_context_payload"),
    "render_conversation_state_prompt": (".context_assembly", "render_conversation_state_prompt"),
    "fallback_planner_result": (".planner", "fallback_planner_result"),
    "normalize_planner_result": (".planner", "normalize_planner_result"),
    "planner_enabled": (".planner", "planner_enabled"),
    "RescueOverlayDayAssessment": (".rescue_overlay", "RescueOverlayDayAssessment"),
    "RescueOverlayTargetDay": (".rescue_overlay", "RescueOverlayTargetDay"),
    "ShortHorizonRescuePlan": (".rescue_overlay", "ShortHorizonRescuePlan"),
    "apply_short_horizon_rescue_plan": (".rescue_overlay", "apply_short_horizon_rescue_plan"),
    "assess_rescue_overlay_day": (".rescue_overlay", "assess_rescue_overlay_day"),
    "build_short_horizon_rescue_plan": (".rescue_overlay", "build_short_horizon_rescue_plan"),
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
