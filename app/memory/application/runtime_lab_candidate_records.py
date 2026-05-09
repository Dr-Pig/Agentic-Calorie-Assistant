from __future__ import annotations

from hashlib import sha256
from typing import Any


def candidate_extraction_artifact(
    *,
    case_results: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    rejections: list[dict[str, Any]],
    runtime_connected: bool,
    live_dogfood_replay: bool,
) -> dict[str, Any]:
    return {
        "artifact_type": "runtime_lab_memory_candidate_extraction",
        "status": "pass" if candidates or rejections else "blocked",
        "activation_stage": "candidate_extraction",
        "semantic_provider_mode": "fake_or_stub_only",
        "case_results": case_results,
        "candidates": candidates,
        "rejections": rejections,
        "candidate_count": len(candidates),
        "rejection_count": len(rejections),
        "runtime_connected": runtime_connected,
        "lab_isolated": True,
        "live_dogfood_replay": live_dogfood_replay,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
        "manager_context_packet_changed": False,
        "shadow_memory_context_pack_used": False,
        "manager_context_injected": False,
    }


def candidate_record(
    *,
    case_id: str,
    candidate_type: str,
    scope_keys: dict[str, str],
    source_refs: list[str],
    payload: dict[str, Any],
    reason_codes: list[str],
    runtime_connected: bool,
) -> dict[str, Any]:
    return {
        "candidate_id": _candidate_id(case_id, candidate_type, source_refs),
        "case_id": case_id,
        "candidate_type": candidate_type,
        "scope_keys": scope_keys,
        "source_trace_ids": [case_id],
        "source_object_refs": source_refs,
        "evidence_count": max(1, len(source_refs)),
        "review_status": str(payload.get("review_status") or "pending"),
        "promotion_allowed_now": bool(payload.get("promotion_allowed_now")),
        "human_review_required": bool(payload.get("human_review_required", True)),
        "reason_codes": reason_codes,
        "payload": payload,
        "extraction_method": "deterministic_trace_contract",
        "semantic_oracle_source": "product_rule_and_trace_fields",
        "raw_keyword_semantic_oracle_used": False,
        "runtime_connected": runtime_connected,
        "lab_isolated": True,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "canonical_mutation_changed": False,
        "manager_context_packet_changed": False,
        "memory_truth_claimed": False,
    }


def rejection_record(case_id: str, reason: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "outcome": "rejected",
        "candidate_type": "none",
        "rejection_reason": reason,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "canonical_mutation_changed": False,
        "manager_context_packet_changed": False,
    }


def _candidate_id(case_id: str, candidate_type: str, source_refs: list[str]) -> str:
    raw = "|".join([case_id, candidate_type, *source_refs])
    return "memory-candidate-" + sha256(raw.encode("utf-8")).hexdigest()[:16]


__all__ = [
    "candidate_extraction_artifact",
    "candidate_record",
    "rejection_record",
]
