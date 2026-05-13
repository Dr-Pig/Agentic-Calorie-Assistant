from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_default_manager_script import (
    build_product_lab_default_manager_script,
)
from app.advanced_shadow_lab.product_lab_manager_selected_context import (
    build_manager_selected_memory_context_adapter,
)
from app.advanced_shadow_lab.product_lab_manager_selected_rescue import (
    build_manager_selected_rescue_artifact,
)
from app.advanced_shadow_lab.product_lab_manager_selected_reusable_meal import (
    build_manager_selected_reusable_meal_artifact,
)
from app.advanced_shadow_lab.product_lab_manager_tool_loop import (
    run_product_lab_manager_tool_loop,
)
from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore


def build_runtime_manager_artifacts(
    *,
    lab_mode: str,
    turn: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
    manager_script: list[Mapping[str, Any]] | None,
    manager_tool_store: ProductLabMemoryStore | None,
) -> dict[str, Any]:
    compiled_manager_script = (
        None
        if manager_script is not None
        else build_product_lab_default_manager_script(
            turn=turn,
            manager_tool_store_present=manager_tool_store is not None,
        )
    )
    effective_manager_script = (
        list(manager_script)
        if manager_script is not None
        else list(_mapping(compiled_manager_script).get("manager_script") or [])
    )
    manager_tool_loop = (
        run_product_lab_manager_tool_loop(
            lab_mode=lab_mode,
            turn=turn,
            fixture_inputs=runtime_inputs,
            manager_script=effective_manager_script,
            store=manager_tool_store,
        )
        if effective_manager_script
        else None
    )
    return {
        "manager_tool_loop_enabled": manager_tool_loop is not None,
        "manager_tool_loop_source": _manager_tool_loop_source(
            explicit_script=manager_script is not None,
            compiled_manager_script=compiled_manager_script,
        ),
        "compiled_default_manager_script": compiled_manager_script,
        "shared_manager_turn_plan_preview": (
            _mapping(_mapping(compiled_manager_script).get("planner_bridge_preview")).get(
                "shared_manager_turn_plan_preview"
            )
            if compiled_manager_script is not None
            else None
        ),
        "manager_selected_memory_context_adapter": (
            build_manager_selected_memory_context_adapter(manager_tool_loop)
        ),
        "manager_selected_rescue_artifact": build_manager_selected_rescue_artifact(
            manager_tool_loop
        ),
        "manager_selected_reusable_meal_artifact": (
            build_manager_selected_reusable_meal_artifact(manager_tool_loop)
        ),
        "manager_tool_loop_artifact": manager_tool_loop,
        "manager_tool_loop_source_refs": _tool_loop_source_refs(manager_tool_loop),
        "manager_tool_loop_blockers": _tool_loop_blockers(manager_tool_loop),
    }


def _manager_tool_loop_source(
    *,
    explicit_script: bool,
    compiled_manager_script: Mapping[str, Any] | None,
) -> str:
    if explicit_script:
        return "explicit_manager_script"
    if compiled_manager_script is None:
        return ""
    return str(compiled_manager_script.get("manager_tool_loop_source") or "")


def _tool_loop_blockers(artifact: Mapping[str, Any] | None) -> list[str]:
    return [] if artifact is None else [str(blocker) for blocker in artifact.get("blockers") or []]


def _tool_loop_source_refs(artifact: Mapping[str, Any] | None) -> list[str]:
    if artifact is None:
        return []
    return [
        f"manager_tool_call:{result.get('call_id') or ''}:{result.get('tool_name') or ''}"
        for result in artifact.get("tool_result_trace") or []
        if isinstance(result, Mapping)
    ]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_runtime_manager_artifacts"]
