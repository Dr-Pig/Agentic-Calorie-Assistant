from __future__ import annotations

import json
from typing import Any

from ..domain import ConversationState
from ..schemas import ContextPackTrace


def _compact_chunk(chunk: Any) -> dict[str, Any]:
    return {
        "chunk_id": str(getattr(chunk, "chunk_id", "")),
        "source_type": str(getattr(chunk, "source_type", "")),
        "content": str(getattr(chunk, "content", "")),
        "linked_meal_id": getattr(chunk, "linked_meal_id", None),
        "score": getattr(chunk, "score", 0.0),
    }


def _compact_open_meal(chunk: Any) -> dict[str, Any]:
    metadata = getattr(chunk, "metadata", {}) or {}
    return {
        "meal_id": getattr(chunk, "source_id", None),
        "title": str(metadata.get("title") or metadata.get("meal_title") or ""),
        "status": str(metadata.get("status") or ""),
        "linked_meal_id": getattr(chunk, "linked_meal_id", None),
    }


def estimate_token_count(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return max(1, len(value) // 4)
    return max(1, len(json.dumps(value, ensure_ascii=False)) // 4)


def build_context_pack_trace(
    *,
    state: ConversationState,
    evidence_bundle: dict[str, Any],
    available_tools: list[str],
    evidence_guardrail_prompt: str,
) -> ContextPackTrace:
    sections = [
        {"name": "evidence_guardrail_prompt", "estimated_tokens": estimate_token_count(evidence_guardrail_prompt)},
        {"name": "session_summary", "estimated_tokens": estimate_token_count(state.session_summary.model_dump(mode="json"))},
        {"name": "active_meal_summary", "estimated_tokens": estimate_token_count(state.active_meal_summary.model_dump(mode="json"))},
        {"name": "recent_turn_summary", "estimated_tokens": estimate_token_count(state.recent_turn_summary.model_dump(mode="json"))},
        {"name": "retrieved_transcript_chunks", "estimated_tokens": estimate_token_count([chunk.model_dump(mode="json") for chunk in state.retrieved_transcript_chunks])},
        {"name": "retrieved_meal_records", "estimated_tokens": estimate_token_count([chunk.model_dump(mode="json") for chunk in state.retrieved_meal_records])},
        {"name": "retrieval_diagnostics", "estimated_tokens": estimate_token_count(state.retrieval_diagnostics)},
        {"name": "durable_memory_hits", "estimated_tokens": estimate_token_count([hit.model_dump(mode="json") for hit in state.durable_memory_hits])},
        {"name": "evidence_bundle", "estimated_tokens": estimate_token_count(evidence_bundle)},
        {"name": "available_tools", "estimated_tokens": estimate_token_count(available_tools)},
    ]
    return ContextPackTrace(
        sections=sections,
        total_estimated_tokens=sum(int(section["estimated_tokens"]) for section in sections),
    )
