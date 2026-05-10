from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_candidate_records import (
    candidate_from_signal,
)
from app.advanced_shadow_lab.product_lab_memory_records import segment_blockers


def extract_product_lab_memory_candidates(
    *,
    session_id: str,
    turn_id: str,
    memory_signal_events: list[Mapping[str, Any]],
) -> dict[str, Any]:
    blockers = segment_blockers(session_id=session_id, turn_id=turn_id)
    candidates: list[dict[str, Any]] = []
    rejections: list[dict[str, str]] = []
    for signal in memory_signal_events:
        candidate, signal_blockers, rejection = candidate_from_signal(
            signal,
            session_id=session_id,
            turn_id=turn_id,
        )
        blockers.extend(signal_blockers)
        if rejection:
            rejections.append(rejection)
        if candidate and not signal_blockers:
            candidates.append(candidate)

    if blockers:
        candidates = []
    return {
        "artifact_type": "advanced_product_lab_memory_candidate_extraction_artifact",
        "status": "blocked" if blockers else "pass",
        "session_id": session_id,
        "turn_id": turn_id,
        "candidate_count": len(candidates),
        "memory_candidates": candidates,
        "rejected_signal_ids": [item["signal_id"] for item in rejections],
        "rejections": rejections,
        "blockers": blockers,
        "raw_transcript_included": False,
        "semantic_inference_used": False,
        "llm_extraction_used": False,
        "no_raw_keyword_semantic_oracle": True,
        "lab_isolated": True,
        "full_product_lab_runtime_enabled": True,
        "lab_memory_store_written": False,
        "memory_write_allowed": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "user_facing_behavior_changed": False,
        "mainline_activation_enabled": False,
    }


__all__ = ["extract_product_lab_memory_candidates"]
