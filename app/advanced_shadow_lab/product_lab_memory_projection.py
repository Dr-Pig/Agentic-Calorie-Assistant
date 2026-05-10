from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_records import mapping
from app.recommendation.application.reviewed_memory_candidate_bridge import (
    build_reviewed_memory_recommendation_three_node_payload,
)


def memory_projection_from_lab_context_pack(
    context_pack: Mapping[str, Any],
) -> dict[str, Any]:
    entries = [entry for entry in context_pack.get("entries") or [] if isinstance(entry, Mapping)]
    positive = _entries_of_type(entries, "preference")
    negative = _entries_of_type(entries, "negative_preference")
    golden = _entries_of_type(entries, "golden_order")
    suppression = _entries_of_type(entries, "interaction_preference")
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass" if context_pack.get("status") == "pass" else "blocked",
        "source_context_pack_artifact_type": context_pack.get("artifact_type"),
        "source_context_pack_used": bool(entries),
        "lab_memory_context_pack_used": bool(entries),
        "preference_profile_summary": {
            "summary_type": "preference_profile_summary",
            "source_kind": "advanced_product_lab_memory_context",
            "is_durable_memory_truth": True,
            "accepted_shadow_candidate_ids": [entry["record_id"] for entry in positive],
            "preference_summaries": [_summary_entry(entry) for entry in positive],
            "negative_preference_blockers": [entry["record_id"] for entry in negative],
        },
        "golden_order_summary": {
            "summary_type": "golden_order_summary",
            "source_kind": "advanced_product_lab_memory_context",
            "is_durable_memory_truth": True,
            "projection_kind": "golden_order_projection_from_product_lab_memory",
            "real_golden_order_materialized": True,
            "orders": [_golden_order(entry) for entry in golden],
        },
        "suppression_summary": {
            "summary_type": "suppression_summary",
            "source_kind": "advanced_product_lab_memory_context",
            "is_durable_memory_truth": True,
            "suppression_blockers": [_suppression(entry) for entry in suppression],
        },
        "omission_trace": list(context_pack.get("omission_trace") or []),
        "runtime_connected": True,
        "lab_isolated": True,
        "summary_first": True,
        "raw_transcript_included": False,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
        "manager_context_packet_changed": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "rescue_proposal_committed": False,
        "retrieval_ranking_changed": False,
    }


def fixture_inputs_with_lab_memory_context(
    fixture_inputs: Mapping[str, Any],
    context_pack: Mapping[str, Any],
) -> dict[str, Any]:
    if not context_pack.get("entries"):
        return dict(fixture_inputs)
    projection = memory_projection_from_lab_context_pack(context_pack)
    return {
        **dict(fixture_inputs),
        "memory_summary_projection": projection,
        "recommendation_payload": _recommendation_payload(fixture_inputs, projection),
    }


def _recommendation_payload(
    fixture_inputs: Mapping[str, Any],
    projection: Mapping[str, Any],
) -> dict[str, Any]:
    if mapping(projection.get("golden_order_summary")).get("orders"):
        return build_reviewed_memory_recommendation_three_node_payload(
            projection,
            remaining_budget_kcal=_remaining_budget_kcal(fixture_inputs),
        )
    payload = dict(mapping(fixture_inputs.get("recommendation_payload")))
    payload["memory_summary_projection"] = projection
    return payload


def _entries_of_type(
    entries: list[Mapping[str, Any]],
    memory_type: str,
) -> list[Mapping[str, Any]]:
    return [entry for entry in entries if entry.get("memory_type") == memory_type]


def _summary_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(entry.get("record_id") or ""),
        "candidate_type": str(entry.get("memory_type") or ""),
        "summary": str(entry.get("summary") or ""),
        "source_object_refs": list(entry.get("source_object_refs") or []),
    }


def _golden_order(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(entry.get("record_id") or ""),
        "store_name": str(entry.get("store_name") or ""),
        "item_names": list(entry.get("item_names") or []),
        "summary": str(entry.get("summary") or ""),
        "estimated_kcal": entry.get("estimated_kcal"),
    }


def _suppression(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(entry.get("record_id") or ""),
        "trigger_type": "advanced_product_lab_chat",
        "summary": str(entry.get("summary") or ""),
    }


def _remaining_budget_kcal(fixture_inputs: Mapping[str, Any]) -> int:
    value = mapping(fixture_inputs.get("current_budget_view")).get("remaining_kcal")
    return value if isinstance(value, int) else 700


__all__ = [
    "fixture_inputs_with_lab_memory_context",
    "memory_projection_from_lab_context_pack",
]
