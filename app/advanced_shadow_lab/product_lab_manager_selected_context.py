from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.context_pack_memory_adapter import (
    build_memory_context_pack_adapter,
)


def build_manager_selected_memory_context_adapter(
    manager_tool_loop_artifact: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(manager_tool_loop_artifact, Mapping):
        return None
    for result in manager_tool_loop_artifact.get("tool_result_trace") or []:
        if not isinstance(result, Mapping):
            continue
        if str(result.get("tool_name") or "") != "memory.search":
            continue
        return build_memory_context_pack_adapter(
            memory_tool_result=_mapping(result.get("result_artifact")),
        )
    return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_manager_selected_memory_context_adapter"]
