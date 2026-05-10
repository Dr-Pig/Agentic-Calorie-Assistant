from __future__ import annotations

from app.advanced_shadow_lab.product_lab_manager_tool_contract import (
    MANAGER_TOOL_NAMES,
    build_product_lab_manager_tool_registry,
)
from app.advanced_shadow_lab.product_lab_manager_tool_dispatch import (
    execute_product_lab_manager_tool_call,
)
from app.advanced_shadow_lab.product_lab_manager_tool_loop import (
    SIDECAR_ACTIVATION_CONTRACT,
    run_product_lab_manager_tool_loop,
)


__all__ = [
    "MANAGER_TOOL_NAMES",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_product_lab_manager_tool_registry",
    "execute_product_lab_manager_tool_call",
    "run_product_lab_manager_tool_loop",
]
