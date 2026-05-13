from __future__ import annotations

from app.advanced_shadow_lab.context_pack_memory_adapter import (
    build_memory_context_pack_adapter,
)


def test_memory_context_pack_adapter_projects_typed_summary_only() -> None:
    artifact = build_memory_context_pack_adapter(
        {
            "context_pack": {
                "selected_record_ids": ["pref-1", "golden-order-2"],
                "source_refs": ["memory_record:pref-1", "meal_thread:mt-2"],
            }
        }
    )

    assert artifact["artifact_type"] == "advanced_product_lab_memory_context_pack_adapter"
    assert artifact["status"] == "pass"
    assert artifact["memory_record_summary"]["selected_record_ids"] == [
        "pref-1",
        "golden-order-2",
    ]
    assert artifact["source_ref_lookup"]["source_ref_count"] == 2
    assert artifact["raw_transcript_included"] is False
