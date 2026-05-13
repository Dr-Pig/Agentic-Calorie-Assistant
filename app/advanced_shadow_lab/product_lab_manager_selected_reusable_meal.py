from __future__ import annotations

from typing import Any, Mapping


def build_manager_selected_reusable_meal_artifact(
    manager_tool_loop_artifact: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(manager_tool_loop_artifact, Mapping):
        return None
    for result in manager_tool_loop_artifact.get("tool_result_trace") or []:
        if not isinstance(result, Mapping):
            continue
        if str(result.get("tool_name") or "") != "reusable_meal.search":
            continue
        artifact = _mapping(result.get("result_artifact"))
        pack = _mapping(artifact.get("typed_context_pack"))
        return {
            "artifact_type": "advanced_product_lab_manager_selected_reusable_meal_artifact",
            "artifact_schema_version": "1.0",
            "status": str(artifact.get("status") or "blocked"),
            "source_call_id": str(result.get("call_id") or ""),
            "reusable_meal_candidates": [
                dict(item)
                for item in pack.get("reusable_meal_candidates") or []
                if isinstance(item, Mapping)
            ],
            "source_ref_lookup": dict(_mapping(artifact.get("source_ref_lookup"))),
            "raw_transcript_included": False,
            "canonical_product_mutation_allowed": False,
            "durable_product_memory_written": False,
            "blockers": [str(blocker) for blocker in artifact.get("blockers") or []],
        }
    return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_manager_selected_reusable_meal_artifact"]
