from __future__ import annotations

from typing import Any

from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _context_candidate_summary(
    candidate: LongTermContextCandidate,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_type": candidate.candidate_type,
        "proposed_memory_text": candidate.proposed_memory_text,
        "confidence": candidate.confidence,
        "freshness_posture": candidate.freshness_posture,
        "source_trace_ids": candidate.source_trace_ids,
        "source_object_refs": candidate.source_object_refs,
        "intended_consumers": candidate.intended_consumers,
        "consumer_use_hints": candidate.consumer_use_hints,
        "risk_if_wrong": candidate.risk_if_wrong,
        "promotion_path": candidate.promotion_path,
        "why_this_is_not_runtime_truth": candidate.why_this_is_not_runtime_truth,
        "runtime_effect_allowed": False,
    }


def _review_status_for_action(action_type: str) -> str:
    if action_type == "accept_candidate":
        return "accepted"
    if action_type == "reject_candidate":
        return "rejected"
    if action_type == "expire_candidate":
        return "expired"
    return "pending"


def _shadow_memory_record(
    candidate: LongTermContextCandidate,
    action_id: str,
) -> dict[str, Any]:
    return {
        "memory_record_id": f"shadow-memory-record-{candidate.candidate_id}",
        "source_candidate_id": candidate.candidate_id,
        "source_action_id": action_id,
        "record_state": "accepted_shadow",
        "memory_text": candidate.proposed_memory_text,
        "candidate_type": candidate.candidate_type,
        "scope_keys": candidate.scope_keys,
        "intended_consumers": candidate.intended_consumers,
        "can_be_runtime_loaded": False,
        "durable_memory_written": False,
        "runtime_effect_allowed": False,
        "provenance": {
            "source_trace_ids": candidate.source_trace_ids,
            "source_object_refs": candidate.source_object_refs,
            "evidence_count": candidate.evidence_count,
        },
    }


def _conversation_summary_preview(candidate: LongTermContextCandidate) -> str:
    summaries = candidate.payload.get("conversation_summaries")
    if isinstance(summaries, list) and summaries and isinstance(summaries[0], dict):
        return str(summaries[0].get("summary") or "")[:280]
    return str(candidate.proposed_memory_text or "")[:280]


def _trigger_type(candidate: LongTermContextCandidate) -> str:
    reason = " ".join(candidate.reason_codes)
    if "overshoot" in reason:
        return "overshoot_risk"
    if "weight" in reason:
        return "weight_logging_consistency"
    if candidate.candidate_type == "golden_order":
        return "weekly_insight_candidate"
    return "high_risk_time_window"
