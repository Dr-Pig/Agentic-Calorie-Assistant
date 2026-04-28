from __future__ import annotations

"""Compatibility facade for Wave 1 intake support modules.

Concrete ownership lives in the dedicated intake_*_tools modules. Keep this
module thin so older import surfaces remain stable while new logic lands in
named seams.
"""

from .intake_estimation_tools import estimate_nutrition_tool
from .intake_persistence_tools import persist_meal_log_tool
from .intake_read_tools import (
    compare_against_budget_tool,
    read_active_meal_tool,
    read_body_plan_tool,
    read_day_budget_tool,
)
from .intake_trace_tools import (
    _normalize_bundle1_live_payload,
    append_trace_event_tool,
    resolve_correction_target_tool,
)

__all__ = [
    "_normalize_bundle1_live_payload",
    "append_trace_event_tool",
    "compare_against_budget_tool",
    "estimate_nutrition_tool",
    "persist_meal_log_tool",
    "read_active_meal_tool",
    "read_body_plan_tool",
    "read_day_budget_tool",
    "resolve_correction_target_tool",
]
