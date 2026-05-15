from __future__ import annotations

import json
from typing import Any


RENDERER_READY_STATUS = "product_pages_renderer_source_map_ready_for_human_review"
TODAY_MACRO_READY_STATUS = "today_macro_mirror_gate_ready_for_human_review"
TODAY_MACRO_RUNTIME_READY_STATUS = "today_macro_runtime_mirror_gate_ready_for_browser"
REQUIRED_MANAGER_RUNTIME_GATES = (
    "rt11c_renderer_input_basis_evidence_pack",
    "rt14_limited_live_ladder",
)
REQUIRED_SELECTORS = (
    "#macro-panel",
    "#macro-guard-reason",
    "#protein-g",
    "#carbs-g",
    "#fat-g",
)
REQUIRED_BACKEND_FIELDS = (
    "payload.consumed_protein",
    "payload.consumed_carbs",
    "payload.consumed_fat",
    "payload.show_macro",
    "payload.macro_guard_reason",
)
REQUIRED_CURRENT_BUDGET_PAYLOAD_FIELDS = (
    "consumed_protein",
    "consumed_carbs",
    "consumed_fat",
    "show_macro",
    "macro_guard_reason",
)
VISIBLE_PAYLOAD = {
    "show_macro": True,
    "macro_guard_reason": "backend hidden reason should not show here",
    "consumed_protein": 31,
    "consumed_carbs": 44,
    "consumed_fat": 12,
}
GUARDED_PAYLOAD = {
    "show_macro": False,
    "macro_guard_reason": "Backend says macros are insufficient today.",
    "consumed_protein": 31,
    "consumed_carbs": 44,
    "consumed_fat": 12,
}


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


__all__ = [
    "GUARDED_PAYLOAD",
    "RENDERER_READY_STATUS",
    "REQUIRED_BACKEND_FIELDS",
    "REQUIRED_CURRENT_BUDGET_PAYLOAD_FIELDS",
    "REQUIRED_MANAGER_RUNTIME_GATES",
    "REQUIRED_SELECTORS",
    "TODAY_MACRO_READY_STATUS",
    "TODAY_MACRO_RUNTIME_READY_STATUS",
    "VISIBLE_PAYLOAD",
    "json_safe",
]
