from __future__ import annotations

from typing import Any, Mapping


def build_memory_context_pack_adapter(
    memory_tool_result: Mapping[str, Any],
) -> dict[str, Any]:
    context_pack = memory_tool_result.get("context_pack") if isinstance(memory_tool_result, Mapping) else {}
    context_pack = context_pack if isinstance(context_pack, Mapping) else {}
    selected_record_ids = [str(item) for item in context_pack.get("selected_record_ids") or []]
    source_refs = [str(item) for item in context_pack.get("source_refs") or []]
    return {
        "artifact_type": "advanced_product_lab_memory_context_pack_adapter",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "memory_record_summary": {
            "selected_record_ids": selected_record_ids,
            "record_count": len(selected_record_ids),
        },
        "source_ref_lookup": {
            "source_refs": source_refs,
            "source_ref_count": len(source_refs),
        },
        "raw_transcript_included": False,
        "blockers": [],
    }


__all__ = ["build_memory_context_pack_adapter"]
