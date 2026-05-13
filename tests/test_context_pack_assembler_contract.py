from __future__ import annotations

from app.shared.contracts.context_pack_assembler import (
    assemble_context_pack_slots,
    build_context_pack_assembler_contract,
)


def test_context_pack_assembler_contract_declares_typed_fields_per_capability() -> None:
    artifact = build_context_pack_assembler_contract()

    assert artifact["artifact_type"] == "shared_context_pack_assembler_contract"
    assert artifact["status"] == "pass"
    assert artifact["typed_context_only"] is True
    assert artifact["raw_transcript_default_allowed"] is False
    assert artifact["capability_context_fields"]["rescue"] == [
        "current_budget_view",
        "active_body_plan_view",
        "open_proposals_view",
        "rescue_history_summary",
    ]


def test_context_pack_assembler_collects_slots_for_requested_capabilities() -> None:
    slots = assemble_context_pack_slots(["memory", "rescue", "reusable_meal"])

    assert slots == {
        "memory": ["memory_record_summary", "source_ref_lookup"],
        "rescue": [
            "current_budget_view",
            "active_body_plan_view",
            "open_proposals_view",
            "rescue_history_summary",
        ],
        "reusable_meal": [
            "canonical_meal_history_refs",
            "memory_record_summary",
            "source_ref_lookup",
        ],
    }
