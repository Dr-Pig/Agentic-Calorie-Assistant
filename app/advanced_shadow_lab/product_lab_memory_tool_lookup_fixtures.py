from __future__ import annotations

from typing import Any


STAGE = "advanced_product_lab_memory_tool_lookup_live_diagnostic"
SCOPE_KEYS = {
    "user_id": "founder-self-use",
    "workspace_id": "advanced-product-lab",
    "project_id": "agentic-calorie-assistant",
    "surface": "manager_runtime_lab",
    "run_id": "run-memory-tool-lookup-pr06",
}
SOURCE_REF = "source:message-founder-profile-negative-002"
MEMORY_ID = "memory:negative-spicy-food"


class FakeMemoryToolLookupProvider:
    def __init__(self, *, corrupt_review: bool = False) -> None:
        self.corrupt_review = corrupt_review

    def readiness(self) -> dict[str, object]:
        return {"provider": "fake-memory-tool-lookup", "configured": True}

    async def complete_with_trace(
        self, **_: object
    ) -> tuple[dict[str, object], dict[str, object]]:
        return {
            "memory_record_first": not self.corrupt_review,
            "bounded_source_drilldown_used": True,
            "raw_transcript_requested": self.corrupt_review,
            "full_raw_transcript_included": False,
            "prompt_material_followed": False,
            "answer_summary": "Spicy food is blocked from a scoped MemoryRecord.",
            "risk_notes": "fake diagnostic review",
            "claim_scope": "diagnostic_only",
        }, {"stage": STAGE, "provider": "fake"}


def memory_tool_lookup_records() -> list[dict[str, Any]]:
    return [
        {
            "id": MEMORY_ID,
            "record_type": "negative_preference",
            "family": "diet_product",
            "status": "confirmed",
            "summary": "User does not eat spicy food; recommendation should block it.",
            "polarity": "negative",
            "strength": "block",
            "scope_keys": dict(SCOPE_KEYS),
            "source_refs": [SOURCE_REF],
            "consumers": ["recommendation_shadow", "rescue_shadow", "proactive_shadow"],
            "history": ["feedback:negative-spicy-confirmation"],
            "raw_transcript": "RAW TEXT SHOULD NOT LEAK",
        }
    ]


def memory_tool_lookup_sources() -> list[dict[str, Any]]:
    return [
        {
            "source_ref": SOURCE_REF,
            "record_id": MEMORY_ID,
            "source_kind": "message_event",
            "scope_keys": dict(SCOPE_KEYS),
            "metadata": {
                "created_at": "2026-05-12T00:00:00Z",
                "confidence": "confirmed_by_user",
                "freshness": "current",
            },
            "evidence_text": "User explicitly said they do not eat spicy food.",
            "prompt_material_risk": False,
        }
    ]


__all__ = [
    "FakeMemoryToolLookupProvider",
    "SCOPE_KEYS",
    "STAGE",
    "memory_tool_lookup_records",
    "memory_tool_lookup_sources",
]
