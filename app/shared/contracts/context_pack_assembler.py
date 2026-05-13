from __future__ import annotations

from typing import Any


CAPABILITY_CONTEXT_FIELDS = {
    "intake": ["recent_chat_turns", "pending_draft", "reusable_meal_candidates"],
    "query": ["current_budget_view", "active_body_plan_view"],
    "memory": ["memory_record_summary", "source_ref_lookup"],
    "recommendation": [
        "memory_record_summary",
        "current_budget_view",
        "active_body_plan_view",
        "reusable_meal_candidates",
    ],
    "rescue": [
        "current_budget_view",
        "active_body_plan_view",
        "open_proposals_view",
        "rescue_history_summary",
    ],
    "proactive": [
        "interaction_preference_summary",
        "suppression_summary",
        "next_signal_summary",
    ],
    "reusable_meal": [
        "canonical_meal_history_refs",
        "memory_record_summary",
        "source_ref_lookup",
    ],
}


def build_context_pack_assembler_contract() -> dict[str, Any]:
    return {
        "artifact_type": "shared_context_pack_assembler_contract",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "capability_context_fields": {
            capability_id: list(fields)
            for capability_id, fields in CAPABILITY_CONTEXT_FIELDS.items()
        },
        "typed_context_only": True,
        "raw_transcript_default_allowed": False,
        "blockers": [],
    }


def assemble_context_pack_slots(requested_capability_ids: list[str]) -> dict[str, list[str]]:
    return {
        capability_id: list(CAPABILITY_CONTEXT_FIELDS[capability_id])
        for capability_id in requested_capability_ids
        if capability_id in CAPABILITY_CONTEXT_FIELDS
    }


__all__ = [
    "CAPABILITY_CONTEXT_FIELDS",
    "assemble_context_pack_slots",
    "build_context_pack_assembler_contract",
]
